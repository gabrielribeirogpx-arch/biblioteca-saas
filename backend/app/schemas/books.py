from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str


class BookOut(BaseModel):
    id: int
    library_id: int
    title: str
    subtitle: str | None = None
    isbn: str | None = None
    edition: str | None = None
    publication_year: int | None = None
    authors: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    marc21_record: dict[str, Any] = Field(default_factory=dict)




class BookListResponse(BaseModel):
    items: list[BookOut]
    page: int
    page_size: int
    total: int


class MARC21ImportRequest(BaseModel):
    record: dict[str, Any]
    category: str = "general"


class MARC21ImportResponse(BaseModel):
    book: BookOut
    normalized_record: dict[str, Any]
    iso2709_base64: str


class MARC21ExportResponse(BaseModel):
    book: BookOut
    normalized_record: dict[str, Any]
    iso2709_base64: str


class AACR2ValidateRequest(BaseModel):
    record: dict[str, Any]
    book_id: int | None = None


class AACR2ValidateResponse(BaseModel):
    valid: bool
    errors: list[str]
    normalized_record: dict[str, Any]


class Z3950LookupRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=25)


class Z3950LookupResponse(BaseModel):
    query: str
    imported_books: list[BookOut]
