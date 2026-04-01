from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookCategory
from app.schemas.books import AdvancedCatalogRequest, BookCreate, BookLookupResponse, BookOut
from app.services.authorities import AuthorityService
from app.services.standards import AACR2Validator, ISO2709Codec, MARC21Service, Z3950Gateway


class BookService:
    @staticmethod
    def _normalize_string_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item).strip() for item in value if str(item).strip()]
        text_value = str(value).strip()
        return [text_value] if text_value else []

    @staticmethod
    def _normalize_marc21_record(value: object) -> dict:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        return {"legacy_payload": value}

    @staticmethod
    def _extract_subfield_value(record: dict, tag: str, code: str) -> str:
        field = record.get(tag)
        if isinstance(field, dict):
            subfields = field.get("subfields")
            if isinstance(subfields, dict):
                value = subfields.get(code, "")
                return str(value).strip()
            return ""
        return str(field).strip() if field is not None else ""

    @staticmethod
    def _validate_advanced_marc_record(record: dict, publication_year: int | None = None) -> list[str]:
        errors: list[str] = []

        title = BookService._extract_subfield_value(record, "245", "a")
        if not title:
            errors.append("Campo 245 (Título) é obrigatório")

        author = BookService._extract_subfield_value(record, "100", "a")
        if not author:
            errors.append("Campo 100 deve conter autor")

        isbn_raw = BookService._extract_subfield_value(record, "020", "a").replace("-", "").replace(" ", "")
        if isbn_raw and not re.fullmatch(r"(?:\d{9}[\dXx]|\d{13})", isbn_raw):
            errors.append("ISBN inválido")

        year_raw = BookService._extract_subfield_value(record, "260", "c")
        if publication_year is not None and publication_year < 0:
            errors.append("Ano deve ser número válido")
        if year_raw and not year_raw.isdigit():
            errors.append("Ano deve ser número válido")

        for tag, field in record.items():
            if not (isinstance(tag, str) and tag.isdigit() and len(tag) == 3):
                continue
            if isinstance(field, dict):
                subfields = field.get("subfields")
                if not isinstance(subfields, dict) or not any(
                    str(code).strip() and str(value).strip() for code, value in subfields.items()
                ):
                    errors.append(f"Campo {tag} deve conter pelo menos 1 subcampo")

        return errors

    @staticmethod
    def build_simplified_marc21_record(
        *,
        control_number: str,
        title: str,
        subtitle: str | None,
        authors: list[str],
        subjects: list[str],
        isbn: str | None,
        publisher: str | None,
        publication_year: int | None,
        pages: int | None,
        edition: str | None,
        language: str | None,
        description: str | None,
    ) -> dict:
        marc_record: dict[str, object] = {
            "001": control_number,
            "100": authors[0] if authors else "",
            "245": f"{title} : {subtitle}" if subtitle else title,
            "260": ", ".join([part for part in [publisher, str(publication_year) if publication_year else None] if part]),
            "300": str(pages) if pages else "",
            "650": subjects,
            "020": isbn or "",
        }
        if edition:
            marc_record["250"] = edition
        if language:
            marc_record["041"] = language
        if description:
            marc_record["520"] = description
        if len(authors) > 1:
            marc_record["700"] = authors[1:]
        return marc_record

    @staticmethod
    async def create_advanced_catalog_record(
        db: AsyncSession,
        payload: AdvancedCatalogRequest,
        library_id: int,
    ) -> tuple[BookOut, dict]:
        title = payload.title.strip()
        subtitle = payload.subtitle.strip() if payload.subtitle else None
        isbn = payload.isbn.strip() if payload.isbn else None
        raw_authors = [author.strip() for author in payload.authors if author.strip()]
        raw_subjects = [subject.strip() for subject in payload.subjects if subject.strip()]
        authors = await AuthorityService.canonicalize_authors(db, raw_authors)
        subjects = await AuthorityService.canonicalize_subjects(db, raw_subjects)

        temporary_control_number = "pending"
        marc21_record = payload.marc21_full or BookService.build_simplified_marc21_record(
            control_number=temporary_control_number,
            title=title,
            subtitle=subtitle,
            authors=authors,
            subjects=subjects,
            isbn=isbn,
            publisher=payload.publisher.strip() if payload.publisher else None,
            publication_year=payload.publication_year,
            pages=payload.pages,
            edition=payload.edition.strip() if payload.edition else None,
            language=payload.language.strip() if payload.language else None,
            description=payload.description.strip() if payload.description else None,
        )
        if isinstance(marc21_record, dict):
            if "100" in marc21_record and isinstance(marc21_record.get("100"), dict):
                field100 = marc21_record["100"]
                subfields = field100.get("subfields") if isinstance(field100, dict) else None
                if isinstance(subfields, dict) and authors:
                    subfields["a"] = authors[0]

            if "650" in marc21_record and isinstance(marc21_record.get("650"), dict):
                field650 = marc21_record["650"]
                subfields = field650.get("subfields") if isinstance(field650, dict) else None
                if isinstance(subfields, dict) and subjects:
                    subfields["a"] = " | ".join(subjects)

            validation_errors = BookService._validate_advanced_marc_record(
                marc21_record,
                publication_year=payload.publication_year,
            )
            if validation_errors:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": validation_errors})

        book = Book(
            library_id=library_id,
            title=title,
            subtitle=subtitle,
            isbn=isbn,
            edition=payload.edition.strip() if payload.edition else None,
            publication_year=payload.publication_year,
            category=BookCategory.GENERAL,
            marc21_record=marc21_record,
            authors=authors,
            subjects=subjects,
            fingerprint_isbn=MARC21Service.hash_fingerprint(isbn) if isbn else None,
            fingerprint_title_author=MARC21Service.hash_fingerprint(f"{title}|{'|'.join(authors)}"),
        )
        db.add(book)
        await db.flush()

        finalized_record = {**marc21_record, "001": str(book.id)} if isinstance(marc21_record, dict) else {"001": str(book.id)}
        book.marc21_record = finalized_record

        await db.commit()
        await db.refresh(book)
        return BookService._to_schema(book), finalized_record

    @staticmethod
    def lookup_by_isbn(isbn: str) -> BookLookupResponse:
        normalized_isbn = isbn.strip()
        suffix = normalized_isbn[-4:] if len(normalized_isbn) >= 4 else normalized_isbn
        year = 2000 + (sum(ord(char) for char in suffix) % 25)
        return BookLookupResponse(
            title=f"Registro importado ISBN {suffix}",
            subtitle="Catalogação assistida",
            authors=["Autor Referencial"],
            subjects=["Catalogação", "Biblioteconomia"],
            isbn=normalized_isbn,
            publisher="Editora Padrão ILS",
            publication_year=year,
            edition="1ª ed.",
            language="pt-BR",
            pages=240,
            description="Registro sugerido por integração simulada de lookup por ISBN.",
        )

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
            authors=BookService._normalize_string_list(book.authors),
            subjects=BookService._normalize_string_list(book.subjects),
            marc21_record=BookService._normalize_marc21_record(book.marc21_record),
        )
