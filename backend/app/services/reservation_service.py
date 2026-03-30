from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copy import Copy, CopyStatus
from app.models.reservation import Reservation, ReservationStatus


class ReservationService:
    HOLD_DAYS = 2

    @staticmethod
    async def create_reservation(db: AsyncSession, library_id: int, user_id: int, copy_id: int) -> Reservation:
        copy = (
            await db.execute(select(Copy).where(Copy.library_id == library_id, Copy.id == copy_id))
        ).scalar_one_or_none()
        if not copy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

        reservation = Reservation(
            library_id=library_id,
            user_id=user_id,
            copy_id=copy_id,
            status=ReservationStatus.QUEUED,
        )
        db.add(reservation)
        if copy.status == CopyStatus.AVAILABLE:
            reservation.status = ReservationStatus.READY
            reservation.expires_at = datetime.now(UTC) + timedelta(days=ReservationService.HOLD_DAYS)
            copy.status = CopyStatus.RESERVED

        await db.commit()
        await db.refresh(reservation)
        return reservation

    @staticmethod
    async def fulfill_next_reservation_for_copy(db: AsyncSession, library_id: int, copy_id: int) -> Reservation | None:
        queue = (
            await db.execute(
                select(Reservation)
                .where(
                    Reservation.library_id == library_id,
                    Reservation.copy_id == copy_id,
                    Reservation.status == ReservationStatus.QUEUED,
                )
                .order_by(Reservation.reserved_at.asc(), Reservation.id.asc())
            )
        ).scalars().first()

        if not queue:
            return None

        queue.status = ReservationStatus.READY
        queue.expires_at = datetime.now(UTC) + timedelta(days=ReservationService.HOLD_DAYS)
        copy = (
            await db.execute(select(Copy).where(Copy.library_id == library_id, Copy.id == copy_id))
        ).scalar_one_or_none()
        if copy:
            copy.status = CopyStatus.RESERVED

        await db.commit()
        await db.refresh(queue)
        return queue

    @staticmethod
    async def expire_ready_reservations(db: AsyncSession, library_id: int) -> int:
        now = datetime.now(UTC)
        reservations = (
            await db.execute(
                select(Reservation).where(
                    Reservation.library_id == library_id,
                    Reservation.status == ReservationStatus.READY,
                    Reservation.expires_at.is_not(None),
                    Reservation.expires_at < now,
                )
            )
        ).scalars().all()

        for reservation in reservations:
            reservation.status = ReservationStatus.EXPIRED

        if reservations:
            await db.commit()
        return len(reservations)
