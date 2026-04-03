from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    TenantScopedContext,
    get_current_user,
    get_db,
    get_tenant_context,
    resolve_context,
    require_librarian,
    require_permission,
    require_user,
)
from app.models.user import User
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.books import (
    AACR2ValidateRequest,
    AACR2ValidateResponse,
    BookCreate,
    BookLookupResponse,
    BookListResponse,
    BookOut,
    MARC21ExportResponse,
    MARC21ImportRequest,
    MARC21ImportResponse,
    Z3950LookupRequest,
    Z3950LookupResponse,
)
from app.services.audit_service import AuditService
from app.services.books import BookService

router = APIRouter()


@router.get("", response_model=BookListResponse, dependencies=[Depends(get_current_user)])
async def list_books(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(resolve_context),
    auth: User = Depends(require_user),
) -> BookListResponse:
    return await BookService.list_books(
        db,
        ctx.tenant.library_id,
        ctx.tenant.tenant_id,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=BookOut, dependencies=[Depends(get_current_user)])
async def create_book(
    payload: BookCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_permission("books.create")),
) -> BookOut:
    created = await BookService.create_book(db, payload, ctx.tenant.library_id)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="books.create",
        entity_type="book",
        entity_id=str(created.id),
        summary="Book created",
        payload=payload.model_dump(),
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return created


@router.post("/import", response_model=MARC21ImportResponse, dependencies=[Depends(get_current_user)])
async def import_marc21(
    payload: MARC21ImportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_librarian),
) -> MARC21ImportResponse:
    book, normalized_record, iso2709_base64 = await BookService.import_marc21_record(
        db=db,
        library_id=ctx.tenant.library_id,
        record=payload.record,
        category=payload.category,
    )
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="books.marc21.import",
        entity_type="book",
        entity_id=str(book.id),
        summary="MARC21 record imported",
        payload={"category": payload.category, "record": normalized_record},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return MARC21ImportResponse(
        book=book,
        normalized_record=normalized_record,
        iso2709_base64=iso2709_base64,
    )


@router.get("/{book_id}/export", response_model=MARC21ExportResponse, dependencies=[Depends(get_current_user)])
async def export_marc21(
    book_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_user),
) -> MARC21ExportResponse:
    book, normalized_record, iso2709_base64 = await BookService.export_marc21_record(
        db=db,
        library_id=ctx.tenant.library_id,
        tenant_id=auth.tenant_id,
        book_id=book_id,
    )

    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="books.marc21.export",
        entity_type="book",
        entity_id=str(book.id),
        summary="MARC21 record exported",
        payload={"book_id": book.id},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )

    return MARC21ExportResponse(
        book=book,
        normalized_record=normalized_record,
        iso2709_base64=iso2709_base64,
    )


@router.post("/validate", response_model=AACR2ValidateResponse, dependencies=[Depends(get_current_user)])
async def validate_aacr2(
    payload: AACR2ValidateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_librarian),
) -> AACR2ValidateResponse:
    valid, errors, normalized_record = await BookService.validate_aacr2_record(
        db=db,
        library_id=ctx.tenant.library_id,
        tenant_id=auth.tenant_id,
        record=payload.record,
        book_id=payload.book_id,
    )

    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="books.aacr2.validate",
        entity_type="book" if payload.book_id else "marc_record",
        entity_id=str(payload.book_id) if payload.book_id else "transient",
        summary="AACR2 validation executed",
        payload={"valid": valid, "errors": errors, "record": normalized_record},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )

    return AACR2ValidateResponse(
        valid=valid,
        errors=errors,
        normalized_record=normalized_record,
    )


@router.post("/lookup", response_model=Z3950LookupResponse, dependencies=[Depends(get_current_user)])
async def lookup_z3950(
    payload: Z3950LookupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_librarian),
) -> Z3950LookupResponse:
    imported_books = await BookService.lookup_and_ingest_z3950(
        db=db,
        library_id=ctx.tenant.library_id,
        query=payload.query,
        limit=payload.limit,
    )

    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="books.z3950.lookup",
        entity_type="integration",
        entity_id="z39.50",
        summary="Z39.50 lookup and ingest completed",
        payload={
            "query": payload.query,
            "limit": payload.limit,
            "imported_book_ids": [book.id for book in imported_books],
        },
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )

    return Z3950LookupResponse(query=payload.query, imported_books=imported_books)


@router.get("/lookup", response_model=BookLookupResponse, dependencies=[Depends(get_current_user)])
async def lookup_by_isbn(
    isbn: str,
    _: User = Depends(require_librarian),
) -> BookLookupResponse:
    return BookService.lookup_by_isbn(isbn)
