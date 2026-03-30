from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantContext, get_db, require_librarian, require_user, resolve_tenant
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.books import BookCreate, BookOut
from app.services.audit_service import AuditService
from app.services.books import BookService

router = APIRouter()


@router.get("/", response_model=list[BookOut])
async def list_books(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_user),
) -> list[BookOut]:
    return BookService.list_books(db, tenant.tenant_id)


@router.post("/", response_model=BookOut)
async def create_book(
    payload: BookCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_librarian),
) -> BookOut:
    created = BookService.create_book(db, payload, tenant.tenant_id)
    await AuditService.log_event(
        db=db,
        library_id=tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action="books.create",
        entity_type="book",
        entity_id=str(created.id),
        summary="Book created",
        payload=payload.model_dump(),
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return created
