from pydantic import BaseModel


class ReportSummary(BaseModel):
    total_books: int
    total_copies: int
    active_loans: int
