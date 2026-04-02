from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.opac import OPACBookDetailResponse, OPACBookListResponse
from app.services.public_catalog import PublicCatalogService

router = APIRouter()


@router.get("/books", response_model=OPACBookListResponse)
async def list_public_books(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    library: str | None = Query(default=None),
    tenant: str | None = Query(default=None),
    isbn: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> OPACBookListResponse:
    return await PublicCatalogService.list_books(
        db,
        page=page,
        page_size=page_size,
        search=search,
        library=library,
        tenant=tenant,
        isbn=isbn,
        subject=subject,
    )


@router.get("/books/{book_id}", response_model=OPACBookDetailResponse)
async def get_public_book(book_id: int, db: AsyncSession = Depends(get_db)) -> OPACBookDetailResponse:
    book = await PublicCatalogService.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book
