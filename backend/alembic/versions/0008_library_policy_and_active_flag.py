"""library policy and active flag

Revision ID: 0008_library_policy_and_active_flag
Revises: 0007_enforce_library_tenant_not_null
Create Date: 2026-04-01 02:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_library_policy_and_active_flag"
down_revision: Union[str, Sequence[str], None] = "0007_enforce_library_tenant_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "libraries",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "library_policies",
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("max_loans", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("loan_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("fine_per_day", sa.Numeric(10, 2), nullable=False, server_default="1.00"),
        sa.Column("renewal_limit", sa.Integer(), nullable=False, server_default="2"),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("library_id"),
    )


def downgrade() -> None:
    op.drop_table("library_policies")
    op.drop_column("libraries", "is_active")
