from __future__ import annotations

import unicodedata

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authority import Author, Subject


class AuthorityService:
    @staticmethod
    def normalize_name(name: str) -> str:
        normalized = unicodedata.normalize("NFKD", name)
        ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
        return " ".join(ascii_text.lower().strip().split())

    @staticmethod
    def _author_autocomplete_query(q: str) -> Select[tuple[Author]]:
        query = select(Author)
        term = q.strip()
        if term:
            query = query.where(Author.name.ilike(f"%{term}%"))
        return query.order_by(Author.name.asc()).limit(20)

    @staticmethod
    async def list_authors(db: AsyncSession, q: str) -> list[Author]:
        result = await db.execute(AuthorityService._author_autocomplete_query(q))
        return list(result.scalars().all())

    @staticmethod
    async def get_or_create_author(db: AsyncSession, name: str) -> Author:
        clean_name = " ".join(name.strip().split())
        normalized = AuthorityService.normalize_name(clean_name)

        existing = (
            await db.execute(select(Author).where(Author.normalized_name == normalized))
        ).scalar_one_or_none()
        if existing:
            return existing

        author = Author(name=clean_name, normalized_name=normalized)
        db.add(author)
        await db.flush()
        return author

    @staticmethod
    async def list_subjects(db: AsyncSession, q: str) -> list[Subject]:
        query = select(Subject)
        term = q.strip()
        if term:
            query = query.where(Subject.name.ilike(f"%{term}%"))
        result = await db.execute(query.order_by(Subject.name.asc()).limit(20))
        return list(result.scalars().all())

    @staticmethod
    async def get_or_create_subject(db: AsyncSession, name: str) -> Subject:
        clean_name = " ".join(name.strip().split())
        existing = (
            await db.execute(select(Subject).where(func.lower(Subject.name) == clean_name.lower()))
        ).scalar_one_or_none()
        if existing:
            return existing

        subject = Subject(name=clean_name)
        db.add(subject)
        await db.flush()
        return subject

    @staticmethod
    async def canonicalize_authors(db: AsyncSession, authors: list[str]) -> list[str]:
        canonical: list[str] = []
        for author in authors:
            if not author.strip():
                continue
            entry = await AuthorityService.get_or_create_author(db, author)
            if entry.name not in canonical:
                canonical.append(entry.name)
        return canonical

    @staticmethod
    async def canonicalize_subjects(db: AsyncSession, subjects: list[str]) -> list[str]:
        canonical: list[str] = []
        for subject in subjects:
            if not subject.strip():
                continue
            entry = await AuthorityService.get_or_create_subject(db, subject)
            if entry.name not in canonical:
                canonical.append(entry.name)
        return canonical
