from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fine import Fine, FineStatus
from app.models.loan import Loan, LoanStatus


class FineService:
    DAILY_OVERDUE_RATE = Decimal("1.00")

    @staticmethod
    async def assess_overdue_fines(db: AsyncSession, library_id: int, tenant_id: int) -> int:
        now = datetime.now(timezone.utc)
        overdue_loans = (
            await db.execute(
                select(Loan).where(
                    Loan.library_id == library_id,
                    Loan.tenant_id == tenant_id,
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                    Loan.due_date < now,
                )
            )
        ).scalars().all()

        created = 0
        for loan in overdue_loans:
            loan.status = LoanStatus.OVERDUE
            existing = (
                await db.execute(select(Fine).where(Fine.library_id == library_id, Fine.tenant_id == tenant_id, Fine.loan_id == loan.id))
            ).scalar_one_or_none()
            overdue_days = max(1, (now.date() - loan.due_date.date()).days)
            amount = Decimal(overdue_days) * FineService.DAILY_OVERDUE_RATE

            if existing:
                existing.amount = amount
                existing.status = FineStatus.PENDING
                existing.reason = f"Auto-updated overdue fine for {overdue_days} day(s)"
            else:
                db.add(
                    Fine(
                        tenant_id=tenant_id,
                        library_id=library_id,
                        user_id=loan.user_id,
                        loan_id=loan.id,
                        amount=amount,
                        currency="USD",
                        status=FineStatus.PENDING,
                        reason=f"Auto-assessed overdue fine for {overdue_days} day(s)",
                    )
                )
                created += 1

        if overdue_loans:
            await db.commit()
        return created

    @staticmethod
    async def settle_fine(
        db: AsyncSession, library_id: int, tenant_id: int, fine_id: int, payment_amount: Decimal
    ) -> Fine | None:
        fine = (
            await db.execute(select(Fine).where(Fine.library_id == library_id, Fine.tenant_id == tenant_id, Fine.id == fine_id))
        ).scalar_one_or_none()
        if not fine:
            return None

        if payment_amount <= Decimal("0"):
            return fine

        remaining = fine.amount - payment_amount
        if remaining <= Decimal("0"):
            fine.amount = Decimal("0")
            fine.status = FineStatus.PAID
        else:
            fine.amount = remaining
            fine.status = FineStatus.PARTIALLY_PAID

        await db.commit()
        await db.refresh(fine)
        return fine

    @staticmethod
    async def has_blocking_fines(db: AsyncSession, library_id: int, tenant_id: int, user_id: int) -> bool:
        fine = (
            await db.execute(
                select(Fine.id).where(
                    Fine.library_id == library_id,
                    Fine.tenant_id == tenant_id,
                    Fine.user_id == user_id,
                    or_(Fine.status == FineStatus.PENDING, Fine.status == FineStatus.PARTIALLY_PAID),
                )
            )
        ).scalar_one_or_none()
        return fine is not None
