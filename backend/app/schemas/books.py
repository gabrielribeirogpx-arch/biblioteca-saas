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




class AdvancedCatalogRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    subtitle: str | None = Field(default=None, max_length=512)
    authors: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    isbn: str | None = Field(default=None, max_length=32)
    publisher: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=0, le=3000)
    edition: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=64)
    pages: int | None = Field(default=None, ge=1, le=100000)
    description: str | None = None


class AdvancedCatalogResponse(BaseModel):
    book: BookOut
    marc21_record: dict[str, Any]


class BookLookupResponse(BaseModel):
    title: str
    subtitle: str | None = None
    authors: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    edition: str | None = None
    language: str | None = None
    pages: int | None = None
    description: str | None = None

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
