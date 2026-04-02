"""reservations queue by book

Revision ID: 0013_reservations_queue_by_book
Revises: 0012_rbac_multi_library_hotfix
Create Date: 2026-04-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0013_reservations_queue_by_book"
down_revision: Union[str, Sequence[str], None] = "0012_rbac_multi_library_hotfix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reservations", sa.Column("book_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE reservations r
        SET book_id = c.book_id
        FROM copies c
        WHERE r.library_id = c.library_id
          AND r.copy_id = c.id
          AND r.book_id IS NULL
        """
    )

    op.alter_column("reservations", "book_id", nullable=False)
    op.alter_column("reservations", "copy_id", nullable=True)

    op.create_foreign_key(
        "fk_reservations_book_tenant",
        "reservations",
        "books",
        ["library_id", "book_id"],
        ["library_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_reservations_library_book_status_position",
        "reservations",
        ["library_id", "book_id", "status", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reservations_library_book_status_position", table_name="reservations")
    op.drop_constraint("fk_reservations_book_tenant", "reservations", type_="foreignkey")

    op.alter_column("reservations", "copy_id", nullable=False)
    op.drop_column("reservations", "book_id")
