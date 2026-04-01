from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Library(Base):
    __tablename__ = "libraries"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_libraries_tenant_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tenant = relationship("Tenant", back_populates="libraries")
    organization = relationship("Organization", back_populates="libraries")
    users = relationship(
        "User",
        back_populates="library",
        cascade="all, delete-orphan",
        overlaps="loans,reservations,fines,agreements,user",
    )
    books = relationship(
        "Book",
        back_populates="library",
        cascade="all, delete-orphan",
        overlaps="copies,book",
    )
    copies = relationship(
        "Copy",
        back_populates="library",
        cascade="all, delete-orphan",
        overlaps="book,copies,loans,reservations,copy",
    )
    loans = relationship(
        "Loan",
        back_populates="library",
        cascade="all, delete-orphan",
        overlaps="user,copy,loans",
    )
    reservations = relationship(
        "Reservation",
        back_populates="library",
        cascade="all, delete-orphan",
        overlaps="user,copy,reservations",
    )
    fines = relationship(
        "Fine",
        back_populates="library",
        cascade="all, delete-orphan",
        overlaps="user,loan,fines",
    )
    agreements = relationship(
        "Agreement",
        back_populates="library",
        cascade="all, delete-orphan",
        overlaps="user,agreements",
    )
    audit_logs = relationship(
        "AuditLog", back_populates="library", cascade="all, delete-orphan"
    )
    sections = relationship("Section", back_populates="library", cascade="all, delete-orphan")
