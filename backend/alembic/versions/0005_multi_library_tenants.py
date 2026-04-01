"""multi-library tenants

Revision ID: 0005_multi_library_tenants
Revises: 0004_multi_unit_organizations
Create Date: 2026-04-01 00:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_multi_library_tenants"
down_revision: Union[str, Sequence[str], None] = "0004_multi_unit_organizations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = [
    "libraries",
    "users",
    "books",
    "copies",
    "loans",
    "reservations",
    "fines",
    "agreements",
    "audit_logs",
    "sections",
]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=False)
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.execute(
        """
        INSERT INTO tenants (name, slug)
        SELECT DISTINCT o.name, o.slug
        FROM organizations o
        LEFT JOIN tenants t ON t.slug = o.slug
        WHERE t.id IS NULL
        """
    )

    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"], unique=False)
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.execute(
        """
        UPDATE libraries AS l
        SET tenant_id = t.id
        FROM organizations AS o
        JOIN tenants AS t ON t.slug = o.slug
        WHERE l.organization_id = o.id
        """
    )
    op.execute(
        """
        UPDATE users AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE books AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE copies AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE loans AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE reservations AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE fines AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE agreements AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE audit_logs AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )
    op.execute(
        """
        UPDATE sections AS x
        SET tenant_id = l.tenant_id
        FROM libraries AS l
        WHERE x.library_id = l.id
        """
    )

    op.create_unique_constraint("uq_libraries_tenant_code", "libraries", ["tenant_id", "code"])


def downgrade() -> None:
    op.drop_constraint("uq_libraries_tenant_code", "libraries", type_="unique")

    for table in reversed(TENANT_TABLES):
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_index("ix_tenants_name", table_name="tenants")
    op.drop_table("tenants")
