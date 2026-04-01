"""library code uniqueness per tenant

Revision ID: 0006_library_code_uniqueness_per_tenant
Revises: 0005_multi_library_tenants
Create Date: 2026-04-01 00:50:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0006_library_code_uniqueness_per_tenant"
down_revision: Union[str, Sequence[str], None] = "0005_multi_library_tenants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_libraries_code", table_name="libraries")
    op.create_index("ix_libraries_code", "libraries", ["code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_libraries_code", table_name="libraries")
    op.create_index("ix_libraries_code", "libraries", ["code"], unique=True)
