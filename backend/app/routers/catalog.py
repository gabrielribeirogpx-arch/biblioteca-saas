from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    TenantScopedContext,
    get_current_user,
    get_db,
    get_tenant_context,
    require_librarian,
)
from app.models.user import User
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.books import AdvancedCatalogRequest, AdvancedCatalogResponse
from app.services.audit_service import AuditService
from app.services.books import BookService

router = APIRouter()


@router.post("/advanced", response_model=AdvancedCatalogResponse, dependencies=[Depends(get_current_user)])
async def create_advanced_catalog_record(
    payload: AdvancedCatalogRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_librarian),
) -> AdvancedCatalogResponse:
    book, marc21_record = await BookService.create_advanced_catalog_record(
        db=db,
        payload=payload,
        library_id=ctx.tenant.library_id,
    )

    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="books.catalog.advanced.create",
        entity_type="book",
        entity_id=str(book.id),
        summary="Advanced catalog record created",
        payload={"book_id": book.id, "marc21_record": marc21_record},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )

    return AdvancedCatalogResponse(book=book, marc21_record=marc21_record)
