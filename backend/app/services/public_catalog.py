from __future__ import annotations

from sqlalchemy import and_, case, cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.copy import Copy
from app.models.library import Library
from app.models.loan import Loan, LoanStatus
from app.models.tenant import Tenant
from app.schemas.opac import (
    OPACBookDetailResponse,
    OPACBookListItem,
    OPACBookListResponse,
    OPACHoldingLibrary,
    OPACLibraryInfo,
)


class PublicCatalogService:
    @staticmethod
    def _normalize_cover_url(isbn: str | None) -> str | None:
        if not isbn:
            return None
        normalized = isbn.replace('-', '').replace(' ', '').strip()
        if not normalized:
            return None
        return f"https://books.google.com/books/content?vid=ISBN{normalized}&printsec=frontcover&img=1&zoom=1&source=gbs_api"

    @staticmethod
    def _author_label(authors: list[str] | None) -> str:
        if not authors:
            return "Autor não informado"
        valid = [author.strip() for author in authors if author and author.strip()]
        return ", ".join(valid) if valid else "Autor não informado"

    @staticmethod
    def _library_info(row: object) -> OPACLibraryInfo:
        return OPACLibraryInfo(
            id=row.library_id,
            name=row.library_name,
            code=row.library_code,
            tenant_id=row.tenant_id,
            tenant_name=row.tenant_name,
            tenant_slug=row.tenant_slug,
        )

    @staticmethod
    def _subject_label(subjects: list[str] | None) -> str | None:
        if not subjects:
            return None
        valid = [subject.strip() for subject in subjects if subject and subject.strip()]
        return ", ".join(valid) if valid else None

    @staticmethod
    def _availability_status(available_copies: int) -> str:
        return "available" if available_copies > 0 else "unavailable"

    @staticmethod
    async def list_books(
        db: AsyncSession,
        *,
        tenant_id: int,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        isbn: str | None = None,
        subject: str | None = None,
    ) -> OPACBookListResponse:
        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        offset = (safe_page - 1) * safe_page_size

        active_loan_case = case((Loan.id.is_not(None), 1), else_=0)
        copy_stats_subquery = (
            select(
                Copy.book_id.label("book_id"),
                func.count(Copy.id).label("total_copies"),
                func.greatest(
                    func.count(Copy.id) - func.coalesce(func.sum(active_loan_case), 0),
                    0,
                ).label("available_copies"),
            )
            .outerjoin(
                Loan,
                and_(
                    Loan.copy_id == Copy.id,
                    Loan.library_id == Copy.library_id,
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                ),
            )
            .group_by(Copy.book_id)
            .subquery()
        )

        base_query = (
            select(
                Book.id,
                Book.title,
                Book.isbn,
                Book.authors,
                Book.subjects,
                Library.id.label("library_id"),
                Library.name.label("library_name"),
                Library.code.label("library_code"),
                Tenant.id.label("tenant_id"),
                Tenant.name.label("tenant_name"),
                Tenant.slug.label("tenant_slug"),
                func.coalesce(copy_stats_subquery.c.total_copies, 0).label("total_copies"),
                func.coalesce(copy_stats_subquery.c.available_copies, 0).label("available_copies"),
            )
            .join(Library, Library.id == Book.library_id)
            .join(Tenant, Tenant.id == Library.tenant_id)
            .outerjoin(copy_stats_subquery, copy_stats_subquery.c.book_id == Book.id)
            .where(Library.is_active.is_(True), Library.tenant_id == tenant_id)
        )

        if search:
            term = f"%{search.strip()}%"
            base_query = base_query.where(
                or_(
                    Book.title.ilike(term),
                    cast(func.array_to_string(Book.authors, " | "), String).ilike(term),
                )
            )

        if isbn:
            base_query = base_query.where(Book.isbn.ilike(f"%{isbn.strip()}%"))

        if subject:
            base_query = base_query.where(cast(func.array_to_string(Book.subjects, " | "), String).ilike(f"%{subject.strip()}%"))

        count_query = select(func.count()).select_from(base_query.order_by(None).subquery())
        total = int(await db.scalar(count_query) or 0)

        result = await db.execute(base_query.order_by(Book.title.asc(), Book.id.asc()).offset(offset).limit(safe_page_size))

        items: list[OPACBookListItem] = []
        for row in result.all():
            available_copies = int(row.available_copies or 0)
            items.append(
                OPACBookListItem(
                    id=row.id,
                    title=row.title,
                    author=PublicCatalogService._author_label(row.authors),
                    isbn=row.isbn,
                    subjects=row.subjects or [],
                    cover_url=PublicCatalogService._normalize_cover_url(row.isbn),
                    available=available_copies > 0,
                    total_copies=int(row.total_copies or 0),
                    available_copies=available_copies,
                    status=PublicCatalogService._availability_status(available_copies),
                    library=PublicCatalogService._library_info(row),
                )
            )

        return OPACBookListResponse(items=items, page=safe_page, page_size=safe_page_size, total=total)

    @staticmethod
    async def get_book(db: AsyncSession, book_id: int, *, tenant_id: int) -> OPACBookDetailResponse | None:
        active_loan_case = case((Loan.id.is_not(None), 1), else_=0)

        row = (
            await db.execute(
                select(
                    Book.id,
                    Book.title,
                    Book.subtitle,
                    Book.isbn,
                    Book.authors,
                    Book.subjects,
                    Book.publication_year,
                    Book.edition,
                    Book.fingerprint_isbn,
                    Book.fingerprint_title_author,
                    Library.id.label("library_id"),
                    Library.name.label("library_name"),
                    Library.code.label("library_code"),
                    Tenant.id.label("tenant_id"),
                    Tenant.name.label("tenant_name"),
                    Tenant.slug.label("tenant_slug"),
                    func.count(Copy.id).label("total_copies"),
                    func.greatest(
                        func.count(Copy.id) - func.coalesce(func.sum(active_loan_case), 0),
                        0,
                    ).label("available_copies"),
                )
                .join(Library, Library.id == Book.library_id)
                .join(Tenant, Tenant.id == Library.tenant_id)
                .outerjoin(Copy, Copy.book_id == Book.id)
                .outerjoin(
                    Loan,
                    and_(
                        Loan.copy_id == Copy.id,
                        Loan.library_id == Copy.library_id,
                        Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                    ),
                )
                .where(Book.id == book_id, Library.is_active.is_(True), Library.tenant_id == tenant_id)
                .group_by(Book.id, Library.id, Tenant.id)
            )
        ).first()

        if not row:
            return None

        related_query = (
            select(
                Library.id.label("library_id"),
                Library.name.label("library_name"),
                Library.code.label("library_code"),
                Tenant.id.label("tenant_id"),
                Tenant.name.label("tenant_name"),
                Tenant.slug.label("tenant_slug"),
                func.count(Copy.id).label("total_copies"),
                func.greatest(
                    func.count(Copy.id) - func.coalesce(func.sum(active_loan_case), 0),
                    0,
                ).label("available_copies"),
            )
            .join(Library, Library.id == Book.library_id)
            .join(Tenant, Tenant.id == Library.tenant_id)
            .outerjoin(Copy, Copy.book_id == Book.id)
            .outerjoin(
                Loan,
                and_(
                    Loan.copy_id == Copy.id,
                    Loan.library_id == Copy.library_id,
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                ),
            )
            .where(Library.is_active.is_(True), Library.tenant_id == tenant_id)
        )

        if row.fingerprint_isbn:
            related_query = related_query.where(Book.fingerprint_isbn == row.fingerprint_isbn)
        else:
            related_query = related_query.where(Book.fingerprint_title_author == row.fingerprint_title_author)

        related_result = await db.execute(related_query.group_by(Library.id, Tenant.id).order_by(Tenant.name.asc(), Library.name.asc()))

        libraries: list[OPACHoldingLibrary] = []
        for library_row in related_result.all():
            available_copies = int(library_row.available_copies or 0)
            libraries.append(
                OPACHoldingLibrary(
                    library=PublicCatalogService._library_info(library_row),
                    total_copies=int(library_row.total_copies or 0),
                    available_copies=available_copies,
                    available=available_copies > 0,
                    status=PublicCatalogService._availability_status(available_copies),
                )
            )

        available_copies = int(row.available_copies or 0)
        return OPACBookDetailResponse(
            id=row.id,
            title=row.title,
            subtitle=row.subtitle,
            author=PublicCatalogService._author_label(row.authors),
            isbn=row.isbn,
            subject=PublicCatalogService._subject_label(row.subjects),
            subjects=row.subjects or [],
            publication_year=row.publication_year,
            edition=row.edition,
            cover_url=PublicCatalogService._normalize_cover_url(row.isbn),
            available=available_copies > 0,
            total_copies=int(row.total_copies or 0),
            available_copies=available_copies,
            status=PublicCatalogService._availability_status(available_copies),
            library=PublicCatalogService._library_info(row),
            libraries=libraries,
        )
