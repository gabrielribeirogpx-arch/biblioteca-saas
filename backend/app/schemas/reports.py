from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    total_books: int
    total_copies: int
    active_loans: int


class MostBorrowedItem(BaseModel):
    book_id: int
    title: str
    checkout_count: int


class OverdueItem(BaseModel):
    loan_id: int
    user_id: int
    copy_id: int
    overdue_days: int


class UsageReport(BaseModel):
    unique_borrowers: int
    loans_created: int
    returns_processed: int
    reservations_created: int


class PerformanceMetrics(BaseModel):
    average_loan_days: float
    overdue_rate: float
    return_rate: float


class TenantReportBundle(BaseModel):
    tenant_id: str
    summary: ReportSummary
    most_borrowed: list[MostBorrowedItem] = Field(default_factory=list)
    overdue: list[OverdueItem] = Field(default_factory=list)
    usage: UsageReport
    performance: PerformanceMetrics
