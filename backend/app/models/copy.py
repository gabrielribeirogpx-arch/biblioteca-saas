from __future__ import annotations

import enum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CopyStatus(str, enum.Enum):
    AVAILABLE = "available"
    ON_LOAN = "on_loan"
    RESERVED = "reserved"
    LOST = "lost"
    DAMAGED = "damaged"


class Copy(Base):
    __tablename__ = "copies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["library_id", "book_id"],
            ["books.library_id", "books.id"],
            ondelete="RESTRICT",
            name="fk_copies_book_tenant",
        ),
        UniqueConstraint("library_id", "id", name="uq_copies_library_id_id"),
        UniqueConstraint("library_id", "barcode", name="uq_copies_library_barcode"),
        Index("ix_copies_library_status", "library_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(nullable=False)

    barcode: Mapped[str] = mapped_column(String(128), nullable=False)
    shelf_location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acquisition_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[CopyStatus] = mapped_column(
        Enum(CopyStatus, name="copy_status", native_enum=True),
        nullable=False,
        default=CopyStatus.AVAILABLE,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    library = relationship(
        "Library",
        back_populates="copies",
        overlaps="book,copies,loans,reservations,copy",
    )
    book = relationship("Book", back_populates="copies", overlaps="library,copies")
    loans = relationship("Loan", back_populates="copy", overlaps="library,loans,user")
    reservations = relationship(
        "Reservation",
        back_populates="copy",
        overlaps="library,reservations,user",
    )
