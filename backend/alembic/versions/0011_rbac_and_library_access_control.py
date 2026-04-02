"""add rbac and user library access control

Revision ID: 0011_rbac_and_library_access_control
Revises: 0010_normalize_library_slug_gpx
Create Date: 2026-04-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_rbac_and_library_access_control"
down_revision: Union[str, Sequence[str], None] = "0010_normalize_library_slug_gpx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("library_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),
    )
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"], unique=False)
    op.create_index("ix_roles_library_id", "roles", ["library_id"], unique=False)
    op.create_index("ix_roles_tenant_library", "roles", ["tenant_id", "library_id"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"], unique=False)
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"], unique=False)

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", "library_id", name="uq_user_roles_user_role_library"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"], unique=False)
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"], unique=False)
    op.create_index("ix_user_roles_tenant_id", "user_roles", ["tenant_id"], unique=False)
    op.create_index("ix_user_roles_library_id", "user_roles", ["library_id"], unique=False)
    op.create_index("ix_user_roles_user_tenant", "user_roles", ["user_id", "tenant_id"], unique=False)

    op.create_table(
        "user_libraries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "library_id", name="uq_user_libraries_user_library"),
    )
    op.create_index("ix_user_libraries_user_id", "user_libraries", ["user_id"], unique=False)
    op.create_index("ix_user_libraries_tenant_id", "user_libraries", ["tenant_id"], unique=False)
    op.create_index("ix_user_libraries_library_id", "user_libraries", ["library_id"], unique=False)
    op.create_index("ix_user_libraries_user_tenant", "user_libraries", ["user_id", "tenant_id"], unique=False)

    op.execute(
        """
        INSERT INTO permissions (code, name, description)
        VALUES
            ('books.read', 'Read books', 'Read books and catalog records'),
            ('books.create', 'Create books', 'Create or import catalog records'),
            ('books.update', 'Update books', 'Edit bibliographic records'),
            ('books.delete', 'Delete books', 'Delete bibliographic records'),
            ('users.read', 'Read users', 'List users for the current tenant/library'),
            ('users.create', 'Create users', 'Create users and assign roles'),
            ('users.update', 'Update users', 'Update users and roles'),
            ('users.delete', 'Delete users', 'Remove users from tenant/library'),
            ('libraries.switch', 'Switch library', 'Switch active library inside tenant')
        ON CONFLICT (code) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO roles (tenant_id, library_id, code, name, description, is_system)
        SELECT DISTINCT u.tenant_id, NULL, 'super_admin', 'Super Admin', 'Full tenant administration', true
        FROM users u
        WHERE u.tenant_id IS NOT NULL
        ON CONFLICT (tenant_id, code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO roles (tenant_id, library_id, code, name, description, is_system)
        SELECT DISTINCT u.tenant_id, NULL, 'librarian', 'Librarian', 'Manage catalog and circulation', true
        FROM users u
        WHERE u.tenant_id IS NOT NULL
        ON CONFLICT (tenant_id, code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO roles (tenant_id, library_id, code, name, description, is_system)
        SELECT DISTINCT u.tenant_id, NULL, 'assistant', 'Assistant', 'Assist operations and circulation', true
        FROM users u
        WHERE u.tenant_id IS NOT NULL
        ON CONFLICT (tenant_id, code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO roles (tenant_id, library_id, code, name, description, is_system)
        SELECT DISTINCT u.tenant_id, NULL, 'member', 'Member', 'Member-level access', true
        FROM users u
        WHERE u.tenant_id IS NOT NULL
        ON CONFLICT (tenant_id, code) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN (
            'books.read', 'books.create', 'books.update', 'books.delete',
            'users.read', 'users.create', 'users.update', 'users.delete',
            'libraries.switch'
        )
        WHERE r.code = 'super_admin'
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN (
            'books.read', 'books.create', 'books.update', 'users.read', 'libraries.switch'
        )
        WHERE r.code = 'librarian'
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN ('books.read', 'users.read', 'libraries.switch')
        WHERE r.code = 'assistant'
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN ('books.read')
        WHERE r.code = 'member'
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id, tenant_id, library_id)
        SELECT u.id, r.id, u.tenant_id, NULL
        FROM users u
        JOIN roles r ON r.tenant_id = u.tenant_id AND r.code = u.role::text
        WHERE u.tenant_id IS NOT NULL
        ON CONFLICT (user_id, role_id, library_id) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO user_libraries (user_id, tenant_id, library_id)
        SELECT u.id, u.tenant_id, u.library_id
        FROM users u
        WHERE u.tenant_id IS NOT NULL
        ON CONFLICT (user_id, library_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_libraries_user_tenant", table_name="user_libraries")
    op.drop_index("ix_user_libraries_library_id", table_name="user_libraries")
    op.drop_index("ix_user_libraries_tenant_id", table_name="user_libraries")
    op.drop_index("ix_user_libraries_user_id", table_name="user_libraries")
    op.drop_table("user_libraries")

    op.drop_index("ix_user_roles_user_tenant", table_name="user_roles")
    op.drop_index("ix_user_roles_library_id", table_name="user_roles")
    op.drop_index("ix_user_roles_tenant_id", table_name="user_roles")
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_tenant_library", table_name="roles")
    op.drop_index("ix_roles_library_id", table_name="roles")
    op.drop_index("ix_roles_tenant_id", table_name="roles")
    op.drop_table("roles")
