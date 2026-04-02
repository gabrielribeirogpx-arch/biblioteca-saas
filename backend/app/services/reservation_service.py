from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.copy import Copy, CopyStatus
from app.models.library import Library
from app.models.reservation import Reservation, ReservationStatus


class ReservationService:
    HOLD_HOURS = 48

    @staticmethod
    async def create_reservation(db: AsyncSession, library_id: int, tenant_id: int, user_id: int, book_id: int) -> Reservation:
        library = (await db.execute(select(Library).where(Library.id == library_id))).scalar_one_or_none()
        book = (
            await db.execute(
                select(Book).where(Book.library_id == library_id, Book.tenant_id == tenant_id, Book.id == book_id)
            )
        ).scalar_one_or_none()
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        copy = (
            await db.execute(
                select(Copy)
                .where(
                    Copy.library_id == library_id,
                    Copy.tenant_id == tenant_id,
                    Copy.book_id == book_id,
                    Copy.status == CopyStatus.AVAILABLE,
                )
                .order_by(Copy.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

        last_position = await db.scalar(
            select(Reservation.position)
            .where(Reservation.library_id == library_id, Reservation.tenant_id == tenant_id, Reservation.book_id == book_id)
            .order_by(Reservation.position.desc())
            .limit(1)
        )

        reservation = Reservation(
            tenant_id=tenant_id if library else None,
            library_id=library_id,
            user_id=user_id,
            book_id=book_id,
            copy_id=copy.id if copy else None,
            status=ReservationStatus.WAITING,
            position=(last_position or 0) + 1,
        )
        db.add(reservation)
        await db.flush()
        if copy:
            await ReservationService.fulfill_next_reservation_for_book(
                db,
                library_id,
                book_id,
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
    async def fulfill_next_reservation_for_book(
        db: AsyncSession,
        library_id: int,
        book_id: int,
        tenant_id: int,
        *,
        auto_commit: bool = True,
    ) -> Reservation | None:
        next_reservation = (
            await db.execute(
                select(Reservation)
                .where(
                    Reservation.library_id == library_id,
                    Reservation.tenant_id == tenant_id,
                    Reservation.book_id == book_id,
                    Reservation.status == ReservationStatus.WAITING,
                )
                .order_by(Reservation.position.asc(), Reservation.reserved_at.asc(), Reservation.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not next_reservation:
            return None

        available_copy = (
            await db.execute(
                select(Copy)
                .where(
                    Copy.library_id == library_id,
                    Copy.tenant_id == tenant_id,
                    Copy.book_id == book_id,
                    Copy.status == CopyStatus.AVAILABLE,
                )
                .order_by(Copy.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not available_copy:
            return None

        next_reservation.copy_id = available_copy.id
        next_reservation.status = ReservationStatus.READY
        next_reservation.expires_at = datetime.now(timezone.utc) + timedelta(hours=ReservationService.HOLD_HOURS)
        available_copy.status = CopyStatus.RESERVED
        if auto_commit:
            await db.commit()
        await db.refresh(next_reservation)
        return next_reservation

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
            await ReservationService.fulfill_next_reservation_for_book(
                db,
                library_id,
                reservation.book_id,
                tenant_id=tenant_id,
                auto_commit=False,
            )

        if reservations:
            await db.commit()
        return len(reservations)

    @staticmethod
    async def process_queue(db: AsyncSession, library_id: int, tenant_id: int) -> int:
        processed = await ReservationService.expire_ready_reservations(db, library_id, tenant_id)
        queued_books = (
            await db.execute(
                select(Reservation.book_id)
                .where(
                    Reservation.library_id == library_id,
                    Reservation.tenant_id == tenant_id,
                    Reservation.status == ReservationStatus.WAITING,
                )
                .group_by(Reservation.book_id)
                .order_by(func.min(Reservation.position).asc(), Reservation.book_id.asc())
            )
        ).scalars().all()

        for book_id in queued_books:
            promoted = await ReservationService.fulfill_next_reservation_for_book(
                db,
                library_id,
                book_id,
                tenant_id=tenant_id,
                auto_commit=False,
            )
            if promoted:
                processed += 1

        await db.commit()
        return processed
