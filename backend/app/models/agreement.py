from __future__ import annotations

import enum
from datetime import datetime

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AgreementCategory(str, enum.Enum):
    MEMBERSHIP = "membership"
    PRIVACY = "privacy"
    DATA_PROCESSING = "data_processing"
    LENDING_POLICY = "lending_policy"


class AgreementStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class Agreement(Base):
    __tablename__ = "agreements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["library_id", "user_id"],
            ["users.library_id", "users.id"],
            ondelete="RESTRICT",
            name="fk_agreements_user_tenant",
        ),
        UniqueConstraint("library_id", "id", name="uq_agreements_library_id_id"),
        Index("ix_agreements_library_category_status", "library_id", "category", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(nullable=False)

    category: Mapped[AgreementCategory] = mapped_column(
        Enum(AgreementCategory, name="agreement_category", native_enum=True), nullable=False
    )
    status: Mapped[AgreementStatus] = mapped_column(
        Enum(AgreementStatus, name="agreement_status", native_enum=True),
        nullable=False,
        default=AgreementStatus.ACTIVE,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    library = relationship("Library", back_populates="agreements", overlaps="user,agreements")
    user = relationship("User", back_populates="agreements", overlaps="library,agreements")
