from pydantic import BaseModel


class CopyCreate(BaseModel):
    book_id: int
    barcode: str


class CopyOut(CopyCreate):
    id: int
    available: bool
