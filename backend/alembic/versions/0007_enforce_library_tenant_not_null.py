"""enforce library tenant not null

Revision ID: 0007_enforce_library_tenant_not_null
Revises: 0006_library_code_uniqueness_per_tenant
Create Date: 2026-04-01 01:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_enforce_library_tenant_not_null"
down_revision: Union[str, Sequence[str], None] = "0006_library_code_uniqueness_per_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE libraries AS l
        SET tenant_id = t.id
        FROM organizations AS o
        JOIN tenants AS t ON t.slug = o.slug
        WHERE l.tenant_id IS NULL
          AND l.organization_id = o.id
        """
    )

    unresolved_count = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM libraries WHERE tenant_id IS NULL")).scalar_one()
    if unresolved_count > 0:
        raise RuntimeError("Security migration aborted: libraries with NULL tenant_id remain")

    op.alter_column("libraries", "tenant_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("libraries", "tenant_id", existing_type=sa.Integer(), nullable=True)
