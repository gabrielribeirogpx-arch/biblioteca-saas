from sqlalchemy.orm import Session

from app.schemas.copies import CopyCreate, CopyOut


class CopyService:
    @staticmethod
    def create_copy(db: Session, payload: CopyCreate, tenant_id: str) -> CopyOut:  # noqa: ARG004
        return CopyOut(id=1, available=True, **payload.model_dump())

    @staticmethod
    def list_copies(db: Session, tenant_id: str) -> list[CopyOut]:  # noqa: ARG004
        return [CopyOut(id=1, book_id=1, barcode=f"{tenant_id}-001", available=True)]
