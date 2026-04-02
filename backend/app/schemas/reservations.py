from datetime import datetime

from pydantic import BaseModel


class ReservationCreate(BaseModel):
    book_id: int


class ReservationOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    copy_id: int | None = None
    position: int
    status: str
    reserved_at: datetime
    expires_at: datetime | None = None


class ReservationListResponse(BaseModel):
    items: list[ReservationOut]
    page: int
    page_size: int
    total: int
