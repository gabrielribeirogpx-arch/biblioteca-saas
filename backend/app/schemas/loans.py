from datetime import date

from pydantic import BaseModel, Field


class LoanCreate(BaseModel):
    user_id: int
    copy_id: int
    due_date: date


class LoanRenewRequest(BaseModel):
    loan_id: int | None = None
    renewal_days: int = Field(default=14, ge=1, le=30)


class LoanOut(LoanCreate):
    id: int
    user_id: str
    status: str


class LoanListResponse(BaseModel):
    items: list[LoanOut]
    page: int
    page_size: int
    total: int
