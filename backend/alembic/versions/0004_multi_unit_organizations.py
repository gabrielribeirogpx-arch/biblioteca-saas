"""multi-unit organization support

Revision ID: 0004_multi_unit_organizations
Revises: 0003_reservation_queue_model
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_multi_unit_organizations"
down_revision: Union[str, Sequence[str], None] = "0003_reservation_queue_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=False)
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.add_column("libraries", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_index("ix_libraries_organization_id", "libraries", ["organization_id"], unique=False)
    op.create_foreign_key(
        "fk_libraries_organization_id",
        "libraries",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        """
        INSERT INTO organizations (name, slug)
        VALUES ('Default Organization', 'default')
        ON CONFLICT (slug) DO NOTHING
        """
    )

    op.execute(
        """
        UPDATE libraries
        SET organization_id = o.id
        FROM organizations o
        WHERE o.slug = 'default' AND libraries.organization_id IS NULL
        """
    )
    op.alter_column("libraries", "organization_id", nullable=False)

    op.create_table(
        "campuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campuses_organization_id", "campuses", ["organization_id"], unique=False)

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sections_library_id", "sections", ["library_id"], unique=False)

    op.add_column("audit_logs", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_audit_logs_organization_id",
        "audit_logs",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"], unique=False)

    op.execute(
        """
        UPDATE audit_logs AS al
        SET organization_id = l.organization_id
        FROM libraries AS l
        WHERE al.library_id = l.id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_organization_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "organization_id")

    op.drop_index("ix_sections_library_id", table_name="sections")
    op.drop_table("sections")

    op.drop_index("ix_campuses_organization_id", table_name="campuses")
    op.drop_table("campuses")

    op.drop_constraint("fk_libraries_organization_id", "libraries", type_="foreignkey")
    op.drop_index("ix_libraries_organization_id", table_name="libraries")
    op.drop_column("libraries", "organization_id")

    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_table("organizations")
