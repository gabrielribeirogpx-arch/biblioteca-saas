from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["library_id", "copy_id"],
            ["copies.library_id", "copies.id"],
            ondelete="RESTRICT",
            name="fk_loans_copy_tenant",
        ),
        ForeignKeyConstraint(
            ["library_id", "user_id"],
            ["users.library_id", "users.id"],
            ondelete="RESTRICT",
            name="fk_loans_user_tenant",
        ),
        UniqueConstraint("library_id", "id", name="uq_loans_library_id_id"),
        Index("ix_loans_library_status_due", "library_id", "status", "due_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(nullable=False)
    copy_id: Mapped[int] = mapped_column(nullable=False)

    checkout_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[LoanStatus] = mapped_column(
        Enum(LoanStatus, name="loan_status", native_enum=True), nullable=False, default=LoanStatus.ACTIVE
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    library = relationship("Library", back_populates="loans", overlaps="user,copy,loans")
    user = relationship("User", back_populates="loans", overlaps="library,copy,loans")
    copy = relationship("Copy", back_populates="loans", overlaps="library,user,loans")
    fine = relationship("Fine", back_populates="loan", uselist=False, overlaps="library,user,fines")
