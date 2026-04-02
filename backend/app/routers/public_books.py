from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_db, resolve_tenant
from app.schemas.opac import OPACBookDetailResponse, OPACBookListResponse
from app.services.public_catalog import PublicCatalogService

router = APIRouter()


@router.get("/books", response_model=OPACBookListResponse)
async def list_public_books(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    isbn: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
) -> OPACBookListResponse:
    return await PublicCatalogService.list_books(
        db,
        tenant_id=tenant.tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        isbn=isbn,
        subject=subject,
    )


@router.get("/books/{book_id}", response_model=OPACBookDetailResponse)
async def get_public_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
) -> OPACBookDetailResponse:
    book = await PublicCatalogService.get_book(db, book_id, tenant_id=tenant.tenant_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book
