from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantContext, get_db, require_librarian, require_user, resolve_tenant
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.copies import CopyCreate, CopyOut
from app.services.audit_service import AuditService
from app.services.copies import CopyService

router = APIRouter()


@router.get("/", response_model=list[CopyOut])
async def list_copies(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_user),
) -> list[CopyOut]:
    return CopyService.list_copies(db, tenant.tenant_id)


@router.post("/", response_model=CopyOut)
async def create_copy(
    payload: CopyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_librarian),
) -> CopyOut:
    created = CopyService.create_copy(db, payload, tenant.tenant_id)
    await AuditService.log_event(
        db=db,
        library_id=tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action="copies.create",
        entity_type="copy",
        entity_id=str(created.id),
        summary="Copy created",
        payload=payload.model_dump(),
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return created
