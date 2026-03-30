from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.copy import Copy
from app.models.loan import Loan, LoanStatus
from app.models.reservation import Reservation
from app.schemas.reports import (
    MostBorrowedItem,
    OverdueItem,
    PerformanceMetrics,
    ReportSummary,
    TenantReportBundle,
    UsageReport,
)


class ReportService:
    @staticmethod
    async def get_summary(db: AsyncSession, library_id: int, tenant_id: str) -> ReportSummary:  # noqa: ARG004
        total_books = await db.scalar(select(func.count()).select_from(Book).where(Book.library_id == library_id))
        total_copies = await db.scalar(select(func.count()).select_from(Copy).where(Copy.library_id == library_id))
        active_loans = await db.scalar(
            select(func.count()).select_from(Loan).where(Loan.library_id == library_id, Loan.status == LoanStatus.ACTIVE)
        )
        return ReportSummary(total_books=total_books or 0, total_copies=total_copies or 0, active_loans=active_loans or 0)

    @staticmethod
    async def most_borrowed(db: AsyncSession, library_id: int, limit: int = 10) -> list[MostBorrowedItem]:
        result = await db.execute(
            select(Book.id, Book.title, func.count(Loan.id).label("checkout_count"))
            .join(Copy, (Copy.library_id == Book.library_id) & (Copy.book_id == Book.id))
            .join(Loan, (Loan.library_id == Copy.library_id) & (Loan.copy_id == Copy.id))
            .where(Book.library_id == library_id)
            .group_by(Book.id, Book.title)
            .order_by(func.count(Loan.id).desc(), Book.id.asc())
            .limit(limit)
        )
        return [MostBorrowedItem(book_id=row.id, title=row.title, checkout_count=row.checkout_count) for row in result]

    @staticmethod
    async def overdue_items(db: AsyncSession, library_id: int, limit: int = 100) -> list[OverdueItem]:
        now = datetime.now(UTC)
        result = await db.execute(
            select(Loan.id, Loan.user_id, Loan.copy_id, Loan.due_date)
            .where(
                Loan.library_id == library_id,
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                Loan.due_date < now,
            )
            .order_by(Loan.due_date.asc())
            .limit(limit)
        )

        items: list[OverdueItem] = []
        for row in result:
            overdue_days = max(1, (now.date() - row.due_date.date()).days)
            items.append(OverdueItem(loan_id=row.id, user_id=row.user_id, copy_id=row.copy_id, overdue_days=overdue_days))
        return items

    @staticmethod
    async def usage_metrics(db: AsyncSession, library_id: int) -> UsageReport:
        unique_borrowers = await db.scalar(
            select(func.count(distinct(Loan.user_id))).where(Loan.library_id == library_id)
        )
        loans_created = await db.scalar(select(func.count()).select_from(Loan).where(Loan.library_id == library_id))
        returns_processed = await db.scalar(
            select(func.count()).select_from(Loan).where(Loan.library_id == library_id, Loan.returned_at.is_not(None))
        )
        reservations_created = await db.scalar(
            select(func.count()).select_from(Reservation).where(Reservation.library_id == library_id)
        )

        return UsageReport(
            unique_borrowers=unique_borrowers or 0,
            loans_created=loans_created or 0,
            returns_processed=returns_processed or 0,
            reservations_created=reservations_created or 0,
        )

    @staticmethod
    async def performance_metrics(db: AsyncSession, library_id: int) -> PerformanceMetrics:
        avg_days = await db.scalar(
            select(
                func.coalesce(
                    func.avg(
                        case(
                            (Loan.returned_at.is_not(None), func.extract("epoch", Loan.returned_at - Loan.checkout_at) / 86400),
                            else_=func.extract("epoch", func.now() - Loan.checkout_at) / 86400,
                        )
                    ),
                    0.0,
                )
            ).where(Loan.library_id == library_id)
        )
        total_loans = await db.scalar(select(func.count()).select_from(Loan).where(Loan.library_id == library_id))
        overdue_loans = await db.scalar(
            select(func.count()).select_from(Loan).where(Loan.library_id == library_id, Loan.status == LoanStatus.OVERDUE)
        )
        returned_loans = await db.scalar(
            select(func.count()).select_from(Loan).where(Loan.library_id == library_id, Loan.status == LoanStatus.RETURNED)
        )

        total = float(total_loans or 0)
        overdue_rate = (float(overdue_loans or 0) / total) if total else 0.0
        return_rate = (float(returned_loans or 0) / total) if total else 0.0
        return PerformanceMetrics(average_loan_days=float(avg_days or 0.0), overdue_rate=overdue_rate, return_rate=return_rate)

    @staticmethod
    async def tenant_bundle(db: AsyncSession, library_id: int, tenant_id: str) -> TenantReportBundle:
        summary = await ReportService.get_summary(db, library_id, tenant_id)
        most_borrowed = await ReportService.most_borrowed(db, library_id)
        overdue = await ReportService.overdue_items(db, library_id)
        usage = await ReportService.usage_metrics(db, library_id)
        performance = await ReportService.performance_metrics(db, library_id)
        return TenantReportBundle(
            tenant_id=tenant_id,
            summary=summary,
            most_borrowed=most_borrowed,
            overdue=overdue,
            usage=usage,
            performance=performance,
        )
