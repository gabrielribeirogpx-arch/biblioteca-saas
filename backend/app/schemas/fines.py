from decimal import Decimal

from pydantic import BaseModel, Field


class FineOut(BaseModel):
    id: int
    user_id: int
    loan_id: int
    amount: Decimal
    currency: str
    status: str
    reason: str | None = None


class FineListResponse(BaseModel):
    items: list[FineOut]
    page: int
    page_size: int
    total: int


class FinePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
