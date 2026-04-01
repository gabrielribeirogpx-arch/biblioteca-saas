from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copy import Copy, CopyStatus
from app.models.library import Library
from app.models.reservation import Reservation, ReservationStatus


class ReservationService:
    HOLD_HOURS = 48

    @staticmethod
    async def create_reservation(db: AsyncSession, library_id: int, tenant_id: int, user_id: int, copy_id: int) -> Reservation:
        library = (await db.execute(select(Library).where(Library.id == library_id))).scalar_one_or_none()
        copy = (
            await db.execute(select(Copy).where(Copy.library_id == library_id, Copy.tenant_id == tenant_id, Copy.id == copy_id))
        ).scalar_one_or_none()
        if not copy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

        last_position = await db.scalar(
            select(Reservation.position)
            .where(Reservation.library_id == library_id, Reservation.tenant_id == tenant_id, Reservation.copy_id == copy_id)
            .order_by(Reservation.position.desc())
            .limit(1)
        )

        reservation = Reservation(
            tenant_id=tenant_id if library else None,
            library_id=library_id,
            user_id=user_id,
            copy_id=copy_id,
            status=ReservationStatus.WAITING,
            position=(last_position or 0) + 1,
        )
        db.add(reservation)
        await db.flush()
        if copy.status == CopyStatus.AVAILABLE:
            await ReservationService.fulfill_next_reservation_for_copy(
                db,
                library_id,
                copy_id,
                tenant_id=tenant_id,
                auto_commit=False,
            )

        await db.commit()
        await db.refresh(reservation)
        return reservation

    @staticmethod
    async def fulfill_next_reservation_for_copy(
        db: AsyncSession,
        library_id: int,
        copy_id: int,
        tenant_id: int,
        *,
        auto_commit: bool = True,
    ) -> Reservation | None:
        queue = (
            await db.execute(
                select(Reservation)
                .where(
                    Reservation.library_id == library_id,
                    Reservation.tenant_id == tenant_id,
                    Reservation.copy_id == copy_id,
                    Reservation.status == ReservationStatus.WAITING,
                )
                .order_by(Reservation.position.asc(), Reservation.reserved_at.asc(), Reservation.id.asc())
            )
        ).scalars().first()

        if not queue:
            return None

        queue.status = ReservationStatus.READY
        queue.expires_at = datetime.now(timezone.utc) + timedelta(hours=ReservationService.HOLD_HOURS)
        copy = (
            await db.execute(select(Copy).where(Copy.library_id == library_id, Copy.tenant_id == tenant_id, Copy.id == copy_id))
        ).scalar_one_or_none()
        if copy:
            copy.status = CopyStatus.RESERVED

        if auto_commit:
            await db.commit()
        await db.refresh(queue)
        return queue

    @staticmethod
    async def expire_ready_reservations(db: AsyncSession, library_id: int, tenant_id: int) -> int:
        now = datetime.now(timezone.utc)
        reservations = (
            await db.execute(
                select(Reservation).where(
                    Reservation.library_id == library_id,
                    Reservation.tenant_id == tenant_id,
                    Reservation.status == ReservationStatus.READY,
                    Reservation.expires_at.is_not(None),
                    Reservation.expires_at < now,
                )
            )
        ).scalars().all()

        for reservation in reservations:
            reservation.status = ReservationStatus.EXPIRED
            reservation.expires_at = now
            await ReservationService.fulfill_next_reservation_for_copy(
                db,
                library_id,
                reservation.copy_id,
                tenant_id=tenant_id,
                auto_commit=False,
            )

        if reservations:
            await db.commit()
        return len(reservations)

    @staticmethod
    async def process_queue(db: AsyncSession, library_id: int, tenant_id: int) -> int:
        processed = await ReservationService.expire_ready_reservations(db, library_id, tenant_id)
        available_copies = (
            await db.execute(
                select(Copy).where(Copy.library_id == library_id, Copy.tenant_id == tenant_id, Copy.status == CopyStatus.AVAILABLE)
            )
        ).scalars().all()

        for copy in available_copies:
            promoted = await ReservationService.fulfill_next_reservation_for_copy(
                db,
                library_id,
                copy.id,
                tenant_id=tenant_id,
                auto_commit=False,
            )
            if promoted:
                processed += 1

        await db.commit()
        return processed
