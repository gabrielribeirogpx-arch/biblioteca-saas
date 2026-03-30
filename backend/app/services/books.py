from sqlalchemy.orm import Session

from app.schemas.books import BookCreate, BookOut


class BookService:
    @staticmethod
    def create_book(db: Session, payload: BookCreate, tenant_id: str) -> BookOut:  # noqa: ARG004
        return BookOut(id=1, tenant_id=tenant_id, **payload.model_dump())

    @staticmethod
    def list_books(db: Session, tenant_id: str) -> list[BookOut]:  # noqa: ARG004
        return [BookOut(id=1, tenant_id=tenant_id, title="Example", author="Unknown", isbn="000")]
