from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FineStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    WAIVED = "waived"


class Fine(Base):
    __tablename__ = "fines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["library_id", "user_id"],
            ["users.library_id", "users.id"],
            ondelete="RESTRICT",
            name="fk_fines_user_tenant",
        ),
        ForeignKeyConstraint(
            ["library_id", "loan_id"],
            ["loans.library_id", "loans.id"],
            ondelete="RESTRICT",
            name="fk_fines_loan_tenant",
        ),
        UniqueConstraint("library_id", "id", name="uq_fines_library_id_id"),
        Index("ix_fines_library_status", "library_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(nullable=False)
    loan_id: Mapped[int] = mapped_column(nullable=False, unique=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[FineStatus] = mapped_column(
        Enum(FineStatus, name="fine_status", native_enum=True), nullable=False, default=FineStatus.PENDING
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    library = relationship("Library", back_populates="fines", overlaps="user,loan,fines")
    user = relationship("User", back_populates="fines", overlaps="library,loan,fines")
    loan = relationship("Loan", back_populates="fine", overlaps="library,user,fines")
