from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copy import Copy, CopyStatus
from app.models.library import Library
from app.schemas.copies import CopyCreate, CopyOut


class CopyService:
    @staticmethod
    async def create_copy(db: AsyncSession, payload: CopyCreate, library_id: int) -> CopyOut:
        library = (await db.execute(select(Library).where(Library.id == library_id))).scalar_one_or_none()
        copy = Copy(
            tenant_id=library.tenant_id if library else None,
            library_id=library_id,
            book_id=payload.book_id,
            barcode=payload.barcode.strip(),
            status=CopyStatus.AVAILABLE,
        )
        db.add(copy)
        await db.commit()
        await db.refresh(copy)
        return CopyOut(id=copy.id, book_id=copy.book_id, barcode=copy.barcode, available=True)

    @staticmethod
    async def list_copies(db: AsyncSession, library_id: int, tenant_id: int) -> list[CopyOut]:
        result = await db.execute(
            select(Copy).where(Copy.library_id == library_id, Copy.tenant_id == tenant_id).order_by(Copy.id.asc())
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

    @staticmethod
    async def search_copies(
        db: AsyncSession,
        library_id: int,
        tenant_id: int,
        query: str,
    ) -> list[CopyOut]:
        normalized_query = query.strip()
        if not normalized_query:
            return await CopyService.list_copies(db, library_id, tenant_id)

        result = await db.execute(
            select(Copy)
            .where(
                Copy.library_id == library_id,
                Copy.tenant_id == tenant_id,
                or_(
                    Copy.barcode.ilike(f"%{normalized_query}%"),
                    cast(Copy.id, String).ilike(f"%{normalized_query}%"),
                ),
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
