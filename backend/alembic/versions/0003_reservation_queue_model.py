"""reservation queue model

Revision ID: 0003_reservation_queue_model
Revises: 0002_authorities
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_reservation_queue_model"
down_revision: Union[str, Sequence[str], None] = "0002_authorities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reservations", sa.Column("position", sa.Integer(), nullable=True))

    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (PARTITION BY library_id, copy_id ORDER BY reserved_at ASC, id ASC) AS row_num
            FROM reservations
        )
        UPDATE reservations AS r
        SET position = ranked.row_num
        FROM ranked
        WHERE r.id = ranked.id
        """
    )

    op.alter_column("reservations", "position", nullable=False)
    op.create_index(
        "ix_reservations_library_copy_status_position",
        "reservations",
        ["library_id", "copy_id", "status", "position"],
        unique=False,
    )

    op.execute("ALTER TYPE reservation_status RENAME TO reservation_status_old")
    op.execute("CREATE TYPE reservation_status AS ENUM ('WAITING', 'READY', 'EXPIRED', 'CANCELLED')")
    op.execute(
        """
        ALTER TABLE reservations
        ALTER COLUMN status TYPE reservation_status
        USING (
            CASE
                WHEN status::text = 'QUEUED' THEN 'WAITING'::reservation_status
                WHEN status::text = 'CANCELED' THEN 'CANCELLED'::reservation_status
                WHEN status::text = 'FULFILLED' THEN 'EXPIRED'::reservation_status
                ELSE status::text::reservation_status
            END
        )
        """
    )
    op.execute("DROP TYPE reservation_status_old")


def downgrade() -> None:
    op.execute("ALTER TYPE reservation_status RENAME TO reservation_status_new")
    op.execute("CREATE TYPE reservation_status AS ENUM ('QUEUED', 'READY', 'FULFILLED', 'CANCELED', 'EXPIRED')")
    op.execute(
        """
        ALTER TABLE reservations
        ALTER COLUMN status TYPE reservation_status
        USING (
            CASE
                WHEN status::text = 'WAITING' THEN 'QUEUED'::reservation_status
                WHEN status::text = 'CANCELLED' THEN 'CANCELED'::reservation_status
                ELSE status::text::reservation_status
            END
        )
        """
    )
    op.execute("DROP TYPE reservation_status_new")

    op.drop_index("ix_reservations_library_copy_status_position", table_name="reservations")
    op.drop_column("reservations", "position")
