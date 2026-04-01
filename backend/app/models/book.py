from __future__ import annotations

import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BookCategory(str, enum.Enum):
    GENERAL = "general"
    REFERENCE = "reference"
    PERIODICAL = "periodical"
    DIGITAL = "digital"
    RARE = "rare"


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint("library_id", "id", name="uq_books_library_id_id"),
        Index("ix_books_library_title", "library_id", "title"),
        Index("ix_books_library_isbn", "library_id", "isbn"),
        Index("ix_books_library_fp_title_author", "library_id", "fingerprint_title_author"),
        Index("ix_books_library_fp_isbn", "library_id", "fingerprint_isbn"),
        Index("ix_books_marc21_record_gin", "marc21_record", postgresql_using="gin"),
        Index("ix_books_authors_gin", "authors", postgresql_using="gin"),
        Index("ix_books_subjects_gin", "subjects", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(512), nullable=True)
    isbn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    edition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(nullable=True)
    category: Mapped[BookCategory] = mapped_column(
        Enum(BookCategory, name="book_category", native_enum=True),
        nullable=False,
        default=BookCategory.GENERAL,
    )

    # MARC21 structured bibliographic record.
    marc21_record: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Authority data fields for canonicalized indexing and retrieval.
    authors: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=list)
    subjects: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=list)

    # Duplicate-detection fingerprints (normalized hashes).
    fingerprint_isbn: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fingerprint_title_author: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    library = relationship("Library", back_populates="books", overlaps="copies,book")
    copies = relationship("Copy", back_populates="book", overlaps="library")
