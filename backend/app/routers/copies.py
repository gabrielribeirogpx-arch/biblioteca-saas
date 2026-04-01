from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AuthContext,
    TenantScopedContext,
    get_current_user,
    get_db,
    get_tenant_context,
    require_librarian,
    require_user,
)
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.copies import CopyCreate, CopyOut
from app.services.audit_service import AuditService
from app.services.copies import CopyService

router = APIRouter()


@router.get("/", response_model=list[CopyOut], dependencies=[Depends(get_current_user)])
async def list_copies(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> list[CopyOut]:
    return await CopyService.list_copies(db, ctx.tenant.library_id)


@router.post("/", response_model=CopyOut, dependencies=[Depends(get_current_user)])
async def create_copy(
    payload: CopyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_librarian),
) -> CopyOut:
    created = await CopyService.create_copy(db, payload, ctx.tenant.library_id)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
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
