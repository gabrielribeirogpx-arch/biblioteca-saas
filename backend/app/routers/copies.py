from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    TenantScopedContext,
    get_current_user,
    get_db,
    resolve_context,
    require_librarian,
    require_user,
)
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.copy import Copy, CopyStatus
from app.models.user import User
from app.schemas.copies import CopyCreate, CopyOut
from app.services.audit_service import AuditService
from app.services.copies import CopyService

router = APIRouter()


@router.get("", response_model=list[CopyOut], dependencies=[Depends(get_current_user)], include_in_schema=False)
@router.get("/", response_model=list[CopyOut], dependencies=[Depends(get_current_user)])
async def list_copies(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(resolve_context),
    _: User = Depends(require_user),
) -> list[CopyOut]:
    result = await db.execute(
        select(Copy)
        .where(
            Copy.tenant_id == ctx.tenant.tenant_id,
            Copy.library_id == ctx.tenant.library_id,
        )
        .order_by(Copy.id.asc())
    )
    copies = result.scalars().all()
    return [
        CopyOut(
            id=copy.id,
            book_id=copy.book_id,
            barcode=copy.barcode,
            available=copy.status == CopyStatus.AVAILABLE,
        )
        for copy in copies
    ]


@router.get("/search", response_model=list[CopyOut], dependencies=[Depends(get_current_user)])
async def search_copies(
    query: str = Query(default="", min_length=0),
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(resolve_context),
    _: User = Depends(require_user),
) -> list[CopyOut]:
    return await CopyService.search_copies(
        db=db,
        library_id=ctx.tenant.library_id,
        tenant_id=ctx.tenant.tenant_id,
        query=query,
    )


@router.post("/", response_model=CopyOut, dependencies=[Depends(get_current_user)])
async def create_copy(
    payload: CopyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(resolve_context),
    auth: User = Depends(require_librarian),
) -> CopyOut:
    created = await CopyService.create_copy(db, payload, ctx.tenant.library_id)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CATALOG,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="copies.create",
        entity_type="copy",
        entity_id=str(created.id),
        summary="Copy created",
        payload=payload.model_dump(),
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return created
