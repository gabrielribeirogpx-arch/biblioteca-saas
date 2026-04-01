from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantScopedContext, get_db, get_tenant_context, require_user
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.fine import Fine, FineStatus
from app.schemas.fines import FineListResponse, FineOut, FinePaymentRequest
from app.services.audit_service import AuditService
from app.services.fine_service import FineService

router = APIRouter()


@router.get('/', response_model=FineListResponse)
async def list_fines(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> FineListResponse:
    offset = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(Fine).where(Fine.library_id == ctx.tenant.library_id))
    result = await db.execute(
        select(Fine)
        .where(Fine.library_id == ctx.tenant.library_id)
        .order_by(Fine.created_at.desc(), Fine.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = [
        FineOut(
            id=row.id,
            user_id=row.user_id,
            loan_id=row.loan_id,
            amount=Decimal(row.amount),
            currency=row.currency,
            status=row.status.value,
            reason=row.reason,
        )
        for row in result.scalars().all()
    ]
    return FineListResponse(items=items, page=page, page_size=page_size, total=total or 0)


@router.post('/{fine_id}/pay', response_model=FineOut)
async def pay_fine(
    fine_id: int,
    payload: FinePaymentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> FineOut:
    fine = await FineService.settle_fine(db, ctx.tenant.library_id, fine_id, payload.amount)
    if not fine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Fine not found')

    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CIRCULATION,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action='fines.pay',
        entity_type='fine',
        entity_id=str(fine.id),
        summary='Fine payment registered',
        payload={'amount': str(payload.amount), 'status': fine.status.value},
        request_id=request.headers.get('x-request-id'),
        ip_address=request.client.host if request.client else None,
    )

    return FineOut(
        id=fine.id,
        user_id=fine.user_id,
        loan_id=fine.loan_id,
        amount=Decimal(fine.amount),
        currency=fine.currency,
        status=fine.status.value,
        reason=fine.reason,
    )
