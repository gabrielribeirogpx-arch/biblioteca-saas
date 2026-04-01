from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookCategory
from app.schemas.books import BookCreate, BookOut
from app.services.standards import AACR2Validator, ISO2709Codec, MARC21Service, Z3950Gateway


class BookService:
    @staticmethod
    async def create_book(db: AsyncSession, payload: BookCreate, library_id: int) -> BookOut:
        authors = [payload.author.strip()] if payload.author.strip() else []
        title = payload.title.strip()
        isbn = payload.isbn.strip() or None

        marc21_record = {
            "leader": "00000nam a2200000 i 4500",
            "control_number": None,
            "fields": [
                {"tag": "020", "ind1": " ", "ind2": " ", "subfields": {"a": isbn or ""}},
                {"tag": "100", "ind1": "1", "ind2": " ", "subfields": {"a": payload.author}},
                {"tag": "245", "ind1": "1", "ind2": "0", "subfields": {"a": payload.title}},
            ],
        }

        book = Book(
            library_id=library_id,
            title=title,
            subtitle=None,
            isbn=isbn,
            edition=None,
            publication_year=None,
            category=BookCategory.GENERAL,
            marc21_record=marc21_record,
            authors=authors,
            subjects=[],
            fingerprint_isbn=MARC21Service.hash_fingerprint(isbn) if isbn else None,
            fingerprint_title_author=MARC21Service.hash_fingerprint(f"{title}|{'|'.join(authors)}"),
        )
        db.add(book)
        await db.commit()
        await db.refresh(book)
        return BookService._to_schema(book)

    @staticmethod
    async def list_books(db: AsyncSession, library_id: int, page: int = 1, page_size: int = 20) -> dict:
        offset = (page - 1) * page_size
        total = await db.scalar(select(func.count()).select_from(Book).where(Book.library_id == library_id))
        result = await db.execute(
            select(Book).where(Book.library_id == library_id).order_by(Book.id.asc()).offset(offset).limit(page_size)
        )
        books = result.scalars().all()
        return {
            "items": [BookService._to_schema(book) for book in books],
            "page": page,
            "page_size": page_size,
            "total": total or 0,
        }

    @staticmethod
    async def import_marc21_record(
        db: AsyncSession,
        library_id: int,
        record: dict,
        category: str,
    ) -> tuple[BookOut, dict, str]:
        normalized = MARC21Service.normalize_record(record)
        mapped = MARC21Service.map_to_book_fields(normalized)
        book_category = BookCategory(category.lower()) if category.lower() in BookCategory._value2member_map_ else BookCategory.GENERAL

        book = Book(
            library_id=library_id,
            category=book_category,
            **mapped,
        )
        db.add(book)
        await db.commit()
        await db.refresh(book)

        encoded = ISO2709Codec.encode_base64(normalized)
        return BookService._to_schema(book), normalized, encoded

    @staticmethod
    async def export_marc21_record(db: AsyncSession, library_id: int, book_id: int) -> tuple[BookOut, dict, str]:
        book = await BookService._get_book(db, library_id, book_id)
        normalized = MARC21Service.normalize_record(book.marc21_record)
        book.marc21_record = normalized
        await db.commit()
        await db.refresh(book)
        return BookService._to_schema(book), normalized, ISO2709Codec.encode_base64(normalized)

    @staticmethod
    async def validate_aacr2_record(
        db: AsyncSession,
        library_id: int,
        record: dict,
        book_id: int | None,
    ) -> tuple[bool, list[str], dict]:
        normalized = MARC21Service.normalize_record(record)
        valid, errors = AACR2Validator.validate(normalized)

        if book_id is not None:
            book = await BookService._get_book(db, library_id, book_id)
            book.marc21_record = normalized
            if valid:
                mapped = MARC21Service.map_to_book_fields(normalized)
                for key in (
                    "title",
                    "subtitle",
                    "isbn",
                    "edition",
                    "publication_year",
                    "authors",
                    "subjects",
                    "fingerprint_isbn",
                    "fingerprint_title_author",
                ):
                    setattr(book, key, mapped[key])
            await db.commit()

        return valid, errors, normalized

    @staticmethod
    async def lookup_and_ingest_z3950(
        db: AsyncSession,
        library_id: int,
        query: str,
        limit: int,
    ) -> list[BookOut]:
        records = Z3950Gateway.lookup(query=query, limit=limit)
        imported: list[BookOut] = []

        for record in records:
            normalized = MARC21Service.normalize_record(record)
            mapped = MARC21Service.map_to_book_fields(normalized)
            book = Book(
                library_id=library_id,
                category=BookCategory.GENERAL,
                **mapped,
            )
            db.add(book)
            await db.flush()
            imported.append(BookService._to_schema(book))

        await db.commit()
        return imported

    @staticmethod
    async def _get_book(db: AsyncSession, library_id: int, book_id: int) -> Book:
        result = await db.execute(select(Book).where(Book.id == book_id, Book.library_id == library_id))
        book = result.scalar_one_or_none()
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        return book

    @staticmethod
    def _to_schema(book: Book) -> BookOut:
        return BookOut(
            id=book.id,
            library_id=book.library_id,
            title=book.title,
            subtitle=book.subtitle,
            isbn=book.isbn,
            edition=book.edition,
            publication_year=book.publication_year,
            authors=book.authors,
            subjects=book.subjects,
            marc21_record=book.marc21_record,
        )
