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


class ReservationStatus(str, enum.Enum):
    QUEUED = "queued"
    READY = "ready"
    FULFILLED = "fulfilled"
    CANCELED = "canceled"
    EXPIRED = "expired"


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["library_id", "copy_id"],
            ["copies.library_id", "copies.id"],
            ondelete="RESTRICT",
            name="fk_reservations_copy_tenant",
        ),
        ForeignKeyConstraint(
            ["library_id", "user_id"],
            ["users.library_id", "users.id"],
            ondelete="RESTRICT",
            name="fk_reservations_user_tenant",
        ),
        UniqueConstraint("library_id", "id", name="uq_reservations_library_id_id"),
        Index("ix_reservations_library_status", "library_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(nullable=False)
    copy_id: Mapped[int] = mapped_column(nullable=False)

    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status", native_enum=True),
        nullable=False,
        default=ReservationStatus.QUEUED,
    )
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    library = relationship("Library", back_populates="reservations")
    user = relationship("User", back_populates="reservations")
    copy = relationship("Copy", back_populates="reservations")
