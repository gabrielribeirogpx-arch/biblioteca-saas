from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantScopedContext, get_db, get_tenant_context, require_librarian, require_user
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.common import MessageResponse
from app.schemas.reservations import ReservationCreate, ReservationListResponse, ReservationOut
from app.services.audit_service import AuditService
from app.services.reservation_service import ReservationService

router = APIRouter()


@router.post('/', response_model=ReservationOut)
async def create_reservation(
    payload: ReservationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> ReservationOut:
    reservation = await ReservationService.create_reservation(db, ctx.tenant.library_id, auth.user_id, payload.copy_id)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CIRCULATION,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action='reservations.create',
        entity_type='reservation',
        entity_id=str(reservation.id),
        summary='Reservation created',
        payload=payload.model_dump(mode='json'),
        request_id=request.headers.get('x-request-id'),
        ip_address=request.client.host if request.client else None,
    )
    return ReservationOut(
        id=reservation.id,
        user_id=reservation.user_id,
        copy_id=reservation.copy_id,
        position=reservation.position,
        status=reservation.status.value,
        reserved_at=reservation.reserved_at,
        expires_at=reservation.expires_at,
    )


@router.get('/', response_model=ReservationListResponse)
async def list_reservations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> ReservationListResponse:
    offset = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(Reservation).where(Reservation.library_id == ctx.tenant.library_id))
    result = await db.execute(
        select(Reservation)
        .where(Reservation.library_id == ctx.tenant.library_id)
        .order_by(Reservation.copy_id.asc(), Reservation.position.asc(), Reservation.id.asc())
        .offset(offset)
        .limit(page_size)
    )
    items = [
        ReservationOut(
            id=row.id,
            user_id=row.user_id,
            copy_id=row.copy_id,
            position=row.position,
            status=row.status.value,
            reserved_at=row.reserved_at,
            expires_at=row.expires_at,
        )
        for row in result.scalars().all()
    ]
    return ReservationListResponse(items=items, page=page, page_size=page_size, total=total or 0)


@router.post('/{reservation_id}/cancel', response_model=MessageResponse)
async def cancel_reservation(
    reservation_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> MessageResponse:
    reservation = (
        await db.execute(
            select(Reservation).where(
                Reservation.library_id == ctx.tenant.library_id,
                Reservation.id == reservation_id,
            )
        )
    ).scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reservation not found')

    reservation.status = ReservationStatus.CANCELLED
    await db.commit()

    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CIRCULATION,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action='reservations.cancel',
        entity_type='reservation',
        entity_id=str(reservation.id),
        summary='Reservation canceled',
        payload=None,
        request_id=request.headers.get('x-request-id'),
        ip_address=request.client.host if request.client else None,
    )
    return MessageResponse(message='Reservation canceled')


@router.post('/process-queue', response_model=MessageResponse)
async def process_reservation_queue(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_librarian),
) -> MessageResponse:
    processed = await ReservationService.process_queue(db, ctx.tenant.library_id)
    return MessageResponse(message=f'Reservation queue processed: {processed} updates')
