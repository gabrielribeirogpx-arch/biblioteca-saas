from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.schemas.search import SearchResult


class SearchService:
    ES_URL = "http://elasticsearch:9200"
    INDEX_PREFIX = "books"

    @staticmethod
    def _index_name(tenant_id: str) -> str:
        return f"{SearchService.INDEX_PREFIX}-{tenant_id}"

    @staticmethod
    def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url=f"{SearchService.ES_URL}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:  # noqa: S310
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {}
            raise

    @staticmethod
    def ensure_index(tenant_id: str) -> None:
        index_name = SearchService._index_name(tenant_id)
        SearchService._request(
            "PUT",
            f"/{index_name}",
            {
                "settings": {"analysis": {"analyzer": {"autocomplete": {"type": "custom", "tokenizer": "standard", "filter": ["lowercase", "edge_ngram"]}}}},
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "library_id": {"type": "integer"},
                        "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}, "autocomplete": {"type": "text", "analyzer": "autocomplete"}}},
                        "subtitle": {"type": "text"},
                        "isbn": {"type": "keyword"},
                        "authors": {"type": "text"},
                        "subjects": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "publication_year": {"type": "integer"},
                        "updated_at": {"type": "date"},
                    }
                },
            },
        )

    @staticmethod
    async def index_book_document(db: AsyncSession, tenant_id: str, library_id: int, book_id: int) -> None:
        SearchService.ensure_index(tenant_id)
        book = (
            await db.execute(select(Book).where(Book.library_id == library_id, Book.id == book_id))
        ).scalar_one_or_none()
        if not book:
            return

        doc = {
            "id": str(book.id),
            "library_id": book.library_id,
            "title": book.title,
            "subtitle": book.subtitle,
            "isbn": book.isbn,
            "authors": book.authors,
            "subjects": book.subjects,
            "category": book.category.value,
            "publication_year": book.publication_year,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        SearchService._request("PUT", f"/{SearchService._index_name(tenant_id)}/_doc/{book.id}", doc)

    @staticmethod
    async def update_book_document(db: AsyncSession, tenant_id: str, library_id: int, book_id: int) -> None:
        await SearchService.index_book_document(db, tenant_id, library_id, book_id)

    @staticmethod
    def delete_book_document(tenant_id: str, book_id: int) -> None:
        SearchService._request("DELETE", f"/{SearchService._index_name(tenant_id)}/_doc/{book_id}")

    @staticmethod
    def search_books(
        tenant_id: str,
        query: str,
        filters: dict[str, Any] | None = None,
        must_terms: list[str] | None = None,
        should_terms: list[str] | None = None,
        must_not_terms: list[str] | None = None,
        autocomplete: bool = False,
    ) -> list[SearchResult]:
        filters = filters or {}
        field = "title.autocomplete" if autocomplete else "title"

        filter_clauses = [{"term": {key: value}} for key, value in filters.items() if value is not None]
        must_clauses = [{"multi_match": {"query": query, "fields": [field, "subtitle", "authors", "subjects"]}}]
        must_clauses.extend({"match": {"title": term}} for term in (must_terms or []))

        body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "should": [{"match": {"title": term}} for term in (should_terms or [])],
                    "must_not": [{"match": {"title": term}} for term in (must_not_terms or [])],
                    "filter": filter_clauses,
                    "minimum_should_match": 0,
                }
            }
        }

        response = SearchService._request("GET", f"/{SearchService._index_name(tenant_id)}/_search", body)
        hits = response.get("hits", {}).get("hits", [])
        return [
            SearchResult(
                id=str(hit.get("_id")),
                score=float(hit.get("_score", 0.0)),
                title=str(hit.get("_source", {}).get("title", "")),
            )
            for hit in hits
        ]
