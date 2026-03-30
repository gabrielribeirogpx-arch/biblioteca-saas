"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-30 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "libraries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_libraries_code", "libraries", ["code"], unique=True)
    op.create_index("ix_libraries_name", "libraries", ["name"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.Enum("AUTH", "CATALOG", "CIRCULATION", "TENANT_ADMIN", "SECURITY", name="audit_category"), nullable=False),
        sa.Column("actor_type", sa.Enum("USER", "SYSTEM", "INTEGRATION", name="audit_actor_type"), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "id", name="uq_audit_logs_library_id_id"),
    )
    op.create_index("ix_audit_logs_library_id", "audit_logs", ["library_id"], unique=False)
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"], unique=False)
    op.create_index("ix_audit_logs_library_category_created", "audit_logs", ["library_id", "category", "created_at"], unique=False)
    op.create_index("ix_audit_logs_library_entity", "audit_logs", ["library_id", "entity_type", "entity_id"], unique=False)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("subtitle", sa.String(length=512), nullable=True),
        sa.Column("isbn", sa.String(length=32), nullable=True),
        sa.Column("edition", sa.String(length=64), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("category", sa.Enum("GENERAL", "REFERENCE", "PERIODICAL", "DIGITAL", "RARE", name="book_category"), nullable=False),
        sa.Column("marc21_record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("authors", postgresql.ARRAY(sa.String(length=255)), nullable=False),
        sa.Column("subjects", postgresql.ARRAY(sa.String(length=255)), nullable=False),
        sa.Column("fingerprint_isbn", sa.String(length=128), nullable=True),
        sa.Column("fingerprint_title_author", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "id", name="uq_books_library_id_id"),
    )
    op.create_index("ix_books_library_id", "books", ["library_id"], unique=False)
    op.create_index("ix_books_library_title", "books", ["library_id", "title"], unique=False)
    op.create_index("ix_books_library_isbn", "books", ["library_id", "isbn"], unique=False)
    op.create_index("ix_books_library_fp_title_author", "books", ["library_id", "fingerprint_title_author"], unique=False)
    op.create_index("ix_books_library_fp_isbn", "books", ["library_id", "fingerprint_isbn"], unique=False)
    op.create_index("ix_books_marc21_record_gin", "books", ["marc21_record"], unique=False, postgresql_using="gin")
    op.create_index("ix_books_authors_gin", "books", ["authors"], unique=False, postgresql_using="gin")
    op.create_index("ix_books_subjects_gin", "books", ["subjects"], unique=False, postgresql_using="gin")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("SUPER_ADMIN", "LIBRARIAN", "ASSISTANT", "MEMBER", name="user_role"), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "id", name="uq_users_library_id_id"),
        sa.UniqueConstraint("library_id", "email", name="uq_users_library_email"),
    )
    op.create_index("ix_users_library_id", "users", ["library_id"], unique=False)
    op.create_index("ix_users_full_name", "users", ["full_name"], unique=False)
    op.create_index("ix_users_library_role", "users", ["library_id", "role"], unique=False)

    op.create_table(
        "agreements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.Enum("MEMBERSHIP", "PRIVACY", "DATA_PROCESSING", "LENDING_POLICY", name="agreement_category"), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "REVOKED", "EXPIRED", name="agreement_status"), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id", "user_id"], ["users.library_id", "users.id"], name="fk_agreements_user_tenant", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "id", name="uq_agreements_library_id_id"),
    )
    op.create_index("ix_agreements_library_id", "agreements", ["library_id"], unique=False)
    op.create_index("ix_agreements_library_category_status", "agreements", ["library_id", "category", "status"], unique=False)

    op.create_table(
        "copies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=128), nullable=False),
        sa.Column("shelf_location", sa.String(length=128), nullable=True),
        sa.Column("acquisition_source", sa.String(length=128), nullable=True),
        sa.Column("status", sa.Enum("AVAILABLE", "ON_LOAN", "RESERVED", "LOST", "DAMAGED", name="copy_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id", "book_id"], ["books.library_id", "books.id"], name="fk_copies_book_tenant", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "barcode", name="uq_copies_library_barcode"),
        sa.UniqueConstraint("library_id", "id", name="uq_copies_library_id_id"),
    )
    op.create_index("ix_copies_library_id", "copies", ["library_id"], unique=False)
    op.create_index("ix_copies_library_status", "copies", ["library_id", "status"], unique=False)

    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("copy_id", sa.Integer(), nullable=False),
        sa.Column("checkout_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "RETURNED", "OVERDUE", "LOST", name="loan_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id", "copy_id"], ["copies.library_id", "copies.id"], name="fk_loans_copy_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["library_id", "user_id"], ["users.library_id", "users.id"], name="fk_loans_user_tenant", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "id", name="uq_loans_library_id_id"),
    )
    op.create_index("ix_loans_library_id", "loans", ["library_id"], unique=False)
    op.create_index("ix_loans_library_status_due", "loans", ["library_id", "status", "due_date"], unique=False)

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("copy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("QUEUED", "READY", "FULFILLED", "CANCELED", "EXPIRED", name="reservation_status"), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id", "copy_id"], ["copies.library_id", "copies.id"], name="fk_reservations_copy_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["library_id", "user_id"], ["users.library_id", "users.id"], name="fk_reservations_user_tenant", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "id", name="uq_reservations_library_id_id"),
    )
    op.create_index("ix_reservations_library_id", "reservations", ["library_id"], unique=False)
    op.create_index("ix_reservations_library_status", "reservations", ["library_id", "status"], unique=False)

    op.create_table(
        "fines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PARTIALLY_PAID", "PAID", "WAIVED", name="fine_status"), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id", "loan_id"], ["loans.library_id", "loans.id"], name="fk_fines_loan_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["library_id", "user_id"], ["users.library_id", "users.id"], name="fk_fines_user_tenant", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loan_id"),
        sa.UniqueConstraint("library_id", "id", name="uq_fines_library_id_id"),
    )
    op.create_index("ix_fines_library_id", "fines", ["library_id"], unique=False)
    op.create_index("ix_fines_library_status", "fines", ["library_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fines_library_status", table_name="fines")
    op.drop_index("ix_fines_library_id", table_name="fines")
    op.drop_table("fines")

    op.drop_index("ix_reservations_library_status", table_name="reservations")
    op.drop_index("ix_reservations_library_id", table_name="reservations")
    op.drop_table("reservations")

    op.drop_index("ix_loans_library_status_due", table_name="loans")
    op.drop_index("ix_loans_library_id", table_name="loans")
    op.drop_table("loans")

    op.drop_index("ix_copies_library_status", table_name="copies")
    op.drop_index("ix_copies_library_id", table_name="copies")
    op.drop_table("copies")

    op.drop_index("ix_agreements_library_category_status", table_name="agreements")
    op.drop_index("ix_agreements_library_id", table_name="agreements")
    op.drop_table("agreements")

    op.drop_index("ix_users_library_role", table_name="users")
    op.drop_index("ix_users_full_name", table_name="users")
    op.drop_index("ix_users_library_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_books_subjects_gin", table_name="books")
    op.drop_index("ix_books_authors_gin", table_name="books")
    op.drop_index("ix_books_marc21_record_gin", table_name="books")
    op.drop_index("ix_books_library_fp_isbn", table_name="books")
    op.drop_index("ix_books_library_fp_title_author", table_name="books")
    op.drop_index("ix_books_library_isbn", table_name="books")
    op.drop_index("ix_books_library_title", table_name="books")
    op.drop_index("ix_books_library_id", table_name="books")
    op.drop_table("books")

    op.drop_index("ix_audit_logs_library_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_library_category_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_library_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_libraries_name", table_name="libraries")
    op.drop_index("ix_libraries_code", table_name="libraries")
    op.drop_table("libraries")

    op.execute("DROP TYPE IF EXISTS fine_status")
    op.execute("DROP TYPE IF EXISTS reservation_status")
    op.execute("DROP TYPE IF EXISTS loan_status")
    op.execute("DROP TYPE IF EXISTS copy_status")
    op.execute("DROP TYPE IF EXISTS agreement_status")
    op.execute("DROP TYPE IF EXISTS agreement_category")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS book_category")
    op.execute("DROP TYPE IF EXISTS audit_actor_type")
    op.execute("DROP TYPE IF EXISTS audit_category")
