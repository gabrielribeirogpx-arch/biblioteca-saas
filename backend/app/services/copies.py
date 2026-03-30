from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.copies import CopyCreate, CopyOut


class CopyService:
    @staticmethod
    def create_copy(db: AsyncSession, payload: CopyCreate, tenant_id: str) -> CopyOut:  # noqa: ARG004
        return CopyOut(id=1, available=True, **payload.model_dump())

    @staticmethod
    def list_copies(db: AsyncSession, tenant_id: str) -> list[CopyOut]:  # noqa: ARG004
        return [CopyOut(id=1, book_id=1, barcode=f"{tenant_id}-001", available=True)]
