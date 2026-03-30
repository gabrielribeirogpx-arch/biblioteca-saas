from pydantic import BaseModel


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str


class BookOut(BookCreate):
    id: int
    tenant_id: str
