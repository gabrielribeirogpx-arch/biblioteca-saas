"""normalize malformed library slug for gpx tenant

Revision ID: 0010_normalize_library_slug_gpx
Revises: 0009_schema_hotfix_resilience
Create Date: 2026-04-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0010_normalize_library_slug_gpx"
down_revision: Union[str, Sequence[str], None] = "0009_schema_hotfix_resilience"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE libraries
        SET code = 'biblioteca-campus-gpx'
        WHERE id = 11 AND code = 'biblioteca---campus-gpx';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE libraries
        SET code = 'biblioteca---campus-gpx'
        WHERE id = 11 AND code = 'biblioteca-campus-gpx';
        """
    )
