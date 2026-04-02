from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import String, func, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantScopedContext, get_db, resolve_context, require_librarian, require_user
from app.models.user import User
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.common import MessageResponse
from app.schemas.reservations import ReservationCreate, ReservationListResponse, ReservationOut
from app.services.audit_service import AuditService
from app.services.reservation_service import ReservationService

router = APIRouter()


def _normalize_reservation_status(raw_status: str | ReservationStatus | None) -> str:
    if raw_status is None:
        return ReservationStatus.WAITING.value
    if isinstance(raw_status, ReservationStatus):
        normalized = raw_status.value.lower()
    else:
        normalized = str(raw_status).lower()
    legacy_status_map = {
        "queued": ReservationStatus.WAITING.value,
        "canceled": ReservationStatus.CANCELLED.value,
        "fulfilled": ReservationStatus.EXPIRED.value,
    }
    return legacy_status_map.get(normalized, normalized)


def _is_missing_position_column_error(exc: ProgrammingError) -> bool:
    error_message = str(getattr(exc, "orig", exc)).lower()
    return "position" in error_message and (
        "undefinedcolumn" in error_message or "does not exist" in error_message
    )


@router.post('/', response_model=ReservationOut)
async def create_reservation(
    payload: ReservationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(resolve_context),
    auth: User = Depends(require_user),
) -> ReservationOut:
    reservation = await ReservationService.create_reservation(
        db,
        ctx.tenant.library_id,
        ctx.tenant.tenant_id,
        auth.id,
        payload.book_id,
    )
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.CIRCULATION,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
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
            book_id=reservation.book_id,
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
    ctx: TenantScopedContext = Depends(resolve_context),
    auth: User = Depends(require_user),
) -> ReservationListResponse:
    offset = (page - 1) * page_size
    total = await db.scalar(
        select(func.count()).select_from(Reservation).where(
            Reservation.library_id == ctx.tenant.library_id,
            Reservation.tenant_id == ctx.tenant.tenant_id,
        )
    )
    reservation_table = Reservation.__table__
    try:
        result = await db.execute(
            select(
                reservation_table.c.id,
                reservation_table.c.user_id,
                reservation_table.c.book_id,
                reservation_table.c.copy_id,
                reservation_table.c.position,
                reservation_table.c.status.cast(String).label("status"),
                reservation_table.c.reserved_at,
                reservation_table.c.expires_at,
            )
            .where(
                reservation_table.c.library_id == ctx.tenant.library_id,
                reservation_table.c.tenant_id == ctx.tenant.tenant_id,
            )
            .order_by(
                reservation_table.c.copy_id.asc(),
                reservation_table.c.book_id.asc(),
                reservation_table.c.position.asc(),
                reservation_table.c.id.asc(),
            )
            .offset(offset)
            .limit(page_size)
        )
    except ProgrammingError as exc:
        if not _is_missing_position_column_error(exc):
            raise

        await db.rollback()
        computed_position = func.row_number().over(
            partition_by=reservation_table.c.book_id,
            order_by=(reservation_table.c.reserved_at.asc(), reservation_table.c.id.asc()),
        )
        result = await db.execute(
            select(
                reservation_table.c.id,
                reservation_table.c.user_id,
                reservation_table.c.book_id,
                reservation_table.c.copy_id,
                computed_position.label("position"),
                reservation_table.c.status.cast(String).label("status"),
                reservation_table.c.reserved_at,
                reservation_table.c.expires_at,
            )
            .where(
                reservation_table.c.library_id == ctx.tenant.library_id,
                reservation_table.c.tenant_id == ctx.tenant.tenant_id,
            )
            .order_by(
                reservation_table.c.book_id.asc(),
                reservation_table.c.reserved_at.asc(),
                reservation_table.c.id.asc(),
            )
            .offset(offset)
            .limit(page_size)
        )
    items = [
        ReservationOut(
            id=record.id,
            user_id=record.user_id,
            book_id=record.book_id,
            copy_id=record.copy_id,
            position=record.position,
            status=_normalize_reservation_status(record.status),
            reserved_at=record.reserved_at,
            expires_at=record.expires_at,
        )
        for record in result.all()
    ]
    return ReservationListResponse(items=items, page=page, page_size=page_size, total=total or 0)


@router.post('/{reservation_id}/cancel', response_model=MessageResponse)
async def cancel_reservation(
    reservation_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(resolve_context),
    auth: User = Depends(require_user),
) -> MessageResponse:
    reservation = (
        await db.execute(
            select(Reservation).where(
                Reservation.library_id == ctx.tenant.library_id,
                Reservation.tenant_id == ctx.tenant.tenant_id,
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
        actor_id=auth.id,
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
    ctx: TenantScopedContext = Depends(resolve_context),
    auth: User = Depends(require_librarian),
) -> MessageResponse:
    processed = await ReservationService.process_queue(db, ctx.tenant.library_id, ctx.tenant.tenant_id)
    return MessageResponse(message=f'Reservation queue processed: {processed} updates')
