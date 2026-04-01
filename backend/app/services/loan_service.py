from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copy import Copy, CopyStatus
from app.models.fine import Fine, FineStatus
from app.models.library import Library
from app.models.loan import Loan, LoanStatus
from app.models.user import User
from app.schemas.loans import LoanCreate, LoanOut
from app.services.reservation_service import ReservationService


class LoanService:
    MAX_RENEWALS = 2
    RENEWAL_WINDOW_DAYS = 14

    @staticmethod
    async def create_loan(db: AsyncSession, payload: LoanCreate, library_id: int, tenant_id: int, user_id: int) -> LoanOut:
        await LoanService._assert_user_not_blocked(db, library_id, tenant_id, user_id)
        library = (await db.execute(select(Library).where(Library.id == library_id))).scalar_one_or_none()

        copy = await LoanService._get_copy(db, library_id, tenant_id, payload.copy_id)
        if copy.status not in {CopyStatus.AVAILABLE, CopyStatus.RESERVED}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Copy is not available for checkout")

        loan = Loan(
            tenant_id=library.tenant_id if library else None,
            library_id=library_id,
            user_id=user_id,
            copy_id=payload.copy_id,
            due_date=datetime.combine(payload.due_date, datetime.min.time(), tzinfo=timezone.utc),
            status=LoanStatus.ACTIVE,
        )
        copy.status = CopyStatus.ON_LOAN
        db.add(loan)
        await db.commit()
        await db.refresh(loan)
        return LoanService._to_schema(loan)

    @staticmethod
    async def list_loans(db: AsyncSession, library_id: int, tenant_id: int, page: int = 1, page_size: int = 20) -> dict:
        await LoanService.mark_overdue_loans(db, library_id, tenant_id)
        offset = (page - 1) * page_size
        total = await db.scalar(
            select(func.count()).select_from(Loan).where(Loan.library_id == library_id, Loan.tenant_id == tenant_id)
        )
        result = await db.execute(
            select(Loan)
            .where(Loan.library_id == library_id, Loan.tenant_id == tenant_id)
            .order_by(Loan.checkout_at.desc(), Loan.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        return {
            "items": [LoanService._to_schema(row) for row in result.scalars().all()],
            "page": page,
            "page_size": page_size,
            "total": total or 0,
        }

    @staticmethod
    async def renew_loan(
        db: AsyncSession, library_id: int, tenant_id: int, loan_id: int, renewal_days: int = RENEWAL_WINDOW_DAYS
    ) -> LoanOut:
        loan = await LoanService._get_loan(db, library_id, tenant_id, loan_id)
        if loan.status != LoanStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active loans can be renewed")

        renewals_count = int((loan.due_date - loan.checkout_at).days / LoanService.RENEWAL_WINDOW_DAYS) - 1
        if renewals_count >= LoanService.MAX_RENEWALS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loan renewal limit reached")

        loan.due_date = loan.due_date + timedelta(days=max(1, renewal_days))
        await db.commit()
        await db.refresh(loan)
        return LoanService._to_schema(loan)

    @staticmethod
    async def return_loan(db: AsyncSession, library_id: int, tenant_id: int, loan_id: int) -> LoanOut:
        loan = await LoanService._get_loan(db, library_id, tenant_id, loan_id)
        if loan.status == LoanStatus.RETURNED:
            return LoanService._to_schema(loan)

        now = datetime.now(timezone.utc)
        loan.returned_at = now
        loan.status = LoanStatus.RETURNED

        copy = await LoanService._get_copy(db, library_id, tenant_id, loan.copy_id)
        copy.status = CopyStatus.AVAILABLE
        await ReservationService.fulfill_next_reservation_for_copy(
            db,
            library_id,
            copy.id,
            tenant_id=tenant_id,
            auto_commit=False,
        )

        if loan.due_date < now:
            overdue_days = max(1, (now.date() - loan.due_date.date()).days)
            existing_fine = (
                await db.execute(
                    select(Fine).where(Fine.library_id == library_id, Fine.tenant_id == tenant_id, Fine.loan_id == loan.id)
                )
            ).scalar_one_or_none()
            if not existing_fine:
                db.add(
                    Fine(
                        tenant_id=tenant_id,
                        library_id=library_id,
                        user_id=loan.user_id,
                        loan_id=loan.id,
                        amount=overdue_days,
                        currency="USD",
                        reason=f"Overdue return by {overdue_days} day(s)",
                        status=FineStatus.PENDING,
                    )
                )

        await db.commit()
        await db.refresh(loan)
        return LoanService._to_schema(loan)

    @staticmethod
    async def mark_overdue_loans(db: AsyncSession, library_id: int, tenant_id: int) -> int:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Loan).where(
                Loan.library_id == library_id,
                Loan.tenant_id == tenant_id,
                Loan.status == LoanStatus.ACTIVE,
                Loan.due_date < now,
            )
        )
        overdue = result.scalars().all()
        for loan in overdue:
            loan.status = LoanStatus.OVERDUE
        if overdue:
            await db.commit()
        return len(overdue)

    @staticmethod
    async def _assert_user_not_blocked(db: AsyncSession, library_id: int, tenant_id: int, user_id: int) -> None:
        user_exists = (
            await db.execute(
                select(User.id).where(
                    User.library_id == library_id,
                    User.tenant_id == tenant_id,
                    User.id == user_id,
                    User.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await LoanService.mark_overdue_loans(db, library_id, tenant_id)

        block_query: Select[tuple[int]] = select(func.count()).select_from(Loan).where(
            Loan.library_id == library_id,
            Loan.tenant_id == tenant_id,
            Loan.user_id == user_id,
            Loan.status == LoanStatus.OVERDUE,
        )
        overdue_count = (await db.execute(block_query)).scalar_one()

        fines_count = (
            await db.execute(
                select(func.count()).select_from(Fine).where(
                    Fine.library_id == library_id,
                    Fine.tenant_id == tenant_id,
                    Fine.user_id == user_id,
                    or_(Fine.status == FineStatus.PENDING, Fine.status == FineStatus.PARTIALLY_PAID),
                )
            )
        ).scalar_one()

        if overdue_count > 0 or fines_count > 0:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked from circulation actions")

    @staticmethod
    async def _get_loan(db: AsyncSession, library_id: int, tenant_id: int, loan_id: int) -> Loan:
        loan = (
            await db.execute(select(Loan).where(Loan.library_id == library_id, Loan.tenant_id == tenant_id, Loan.id == loan_id))
        ).scalar_one_or_none()
        if not loan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
        return loan

    @staticmethod
    async def _get_copy(db: AsyncSession, library_id: int, tenant_id: int, copy_id: int) -> Copy:
        copy = (
            await db.execute(select(Copy).where(Copy.library_id == library_id, Copy.tenant_id == tenant_id, Copy.id == copy_id))
        ).scalar_one_or_none()
        if not copy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")
        return copy

    @staticmethod
    def _to_schema(loan: Loan) -> LoanOut:
        return LoanOut(
            id=loan.id,
            copy_id=loan.copy_id,
            due_date=date.fromisoformat(loan.due_date.date().isoformat()),
            user_id=str(loan.user_id),
            status=loan.status.value,
        )
