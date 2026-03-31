from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copy import Copy, CopyStatus
from app.schemas.copies import CopyCreate, CopyOut


class CopyService:
    @staticmethod
    async def create_copy(db: AsyncSession, payload: CopyCreate, library_id: int) -> CopyOut:
        copy = Copy(
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
    async def list_copies(db: AsyncSession, library_id: int) -> list[CopyOut]:
        result = await db.execute(select(Copy).where(Copy.library_id == library_id).order_by(Copy.id.asc()))
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
