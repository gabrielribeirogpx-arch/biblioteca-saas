from __future__ import annotations

import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    LIBRARIAN = "librarian"
    ASSISTANT = "assistant"
    MEMBER = "member"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("library_id", "id", name="uq_users_library_id_id"),
        UniqueConstraint("library_id", "email", name="uq_users_library_email"),
        Index("ix_users_library_role", "library_id", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True), nullable=False, default=UserRole.MEMBER
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    library = relationship("Library", back_populates="users")
    loans = relationship("Loan", back_populates="user")
    reservations = relationship("Reservation", back_populates="user")
    fines = relationship("Fine", back_populates="user")
    agreements = relationship("Agreement", back_populates="user")
