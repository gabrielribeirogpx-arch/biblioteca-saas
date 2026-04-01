"""schema hotfix resilience for production consistency

Revision ID: 0009_schema_hotfix_resilience
Revises: 0008_library_policy_and_active_flag
Create Date: 2026-04-01 03:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0009_schema_hotfix_resilience"
down_revision: Union[str, Sequence[str], None] = "0008_library_policy_and_active_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _column_type_name(inspector: sa.Inspector, table_name: str, column_name: str) -> str:
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return str(column["type"]).lower()
    return ""


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _column_exists(inspector, "libraries", "is_active") is False:
        op.add_column(
            "libraries",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )

    libraries_code_type = _column_type_name(inspector, "libraries", "code")
    if "character varying(100)" not in libraries_code_type:
        op.alter_column(
            "libraries",
            "code",
            existing_type=sa.String(),
            type_=sa.String(length=100),
            existing_nullable=False,
        )

    if _column_exists(inspector, "tenants", "code"):
        tenants_code_type = _column_type_name(inspector, "tenants", "code")
        if "character varying(100)" not in tenants_code_type:
            op.alter_column(
                "tenants",
                "code",
                existing_type=sa.String(),
                type_=sa.String(length=100),
                existing_nullable=False,
            )


def downgrade() -> None:
    pass
