from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LibraryPolicy(Base):
    __tablename__ = "library_policies"

    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), primary_key=True
    )
    max_loans: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    loan_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14, server_default="14")
    fine_per_day: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("1.00"), server_default="1.00"
    )
    renewal_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")

    library = relationship("Library", back_populates="policy")
