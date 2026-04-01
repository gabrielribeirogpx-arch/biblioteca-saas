from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Library(Base):
    __tablename__ = "libraries"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization = relationship("Organization", back_populates="libraries")
    users = relationship("User", back_populates="library", cascade="all, delete-orphan")
    books = relationship("Book", back_populates="library", cascade="all, delete-orphan")
    copies = relationship("Copy", back_populates="library", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="library", cascade="all, delete-orphan")
    reservations = relationship(
        "Reservation", back_populates="library", cascade="all, delete-orphan"
    )
    fines = relationship("Fine", back_populates="library", cascade="all, delete-orphan")
    agreements = relationship(
        "Agreement", back_populates="library", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="library", cascade="all, delete-orphan"
    )
    sections = relationship("Section", back_populates="library", cascade="all, delete-orphan")
