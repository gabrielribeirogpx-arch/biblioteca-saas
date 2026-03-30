from __future__ import annotations

import hashlib
from typing import Any


class MARC21Service:
    """Utility service for MARC21 normalization and metadata mapping."""

    @staticmethod
    def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
        fields = record.get("fields") or []
        normalized_fields: list[dict[str, Any]] = []

        for field in fields:
            tag = str(field.get("tag", "")).strip().zfill(3)[:3]
            ind1 = str(field.get("ind1", " ") or " ")[:1]
            ind2 = str(field.get("ind2", " ") or " ")[:1]

            raw_subfields = field.get("subfields") or {}
            normalized_subfields: dict[str, Any] = {}
            for code, value in raw_subfields.items():
                normalized_code = str(code).strip().lower()[:1]
                if isinstance(value, list):
                    normalized_subfields[normalized_code] = [
                        str(item).strip() for item in value if str(item).strip()
                    ]
                else:
                    normalized_subfields[normalized_code] = str(value).strip()

            normalized_fields.append(
                {
                    "tag": tag,
                    "ind1": ind1,
                    "ind2": ind2,
                    "subfields": normalized_subfields,
                }
            )

        normalized_fields.sort(key=lambda item: item["tag"])
        return {
            "leader": str(record.get("leader", "")).strip(),
            "control_number": str(record.get("control_number", "")).strip() or None,
            "fields": normalized_fields,
        }

    @staticmethod
    def map_to_book_fields(record: dict[str, Any]) -> dict[str, Any]:
        normalized = MARC21Service.normalize_record(record)

        title_field = MARC21Service._first_field(normalized, "245")
        author_fields = MARC21Service._all_fields(normalized, {"100", "700"})
        subject_fields = MARC21Service._all_fields(normalized, {"650", "651"})
        isbn_field = MARC21Service._first_field(normalized, "020")
        edition_field = MARC21Service._first_field(normalized, "250")
        publication_field = MARC21Service._first_field(normalized, "264") or MARC21Service._first_field(
            normalized, "260"
        )

        title = MARC21Service._extract_subfield(title_field, "a") or "Untitled"
        subtitle = MARC21Service._extract_subfield(title_field, "b")

        authors = [
            MARC21Service._extract_subfield(field, "a")
            for field in author_fields
            if MARC21Service._extract_subfield(field, "a")
        ]

        subjects = [
            MARC21Service._extract_subfield(field, "a")
            for field in subject_fields
            if MARC21Service._extract_subfield(field, "a")
        ]

        isbn_raw = MARC21Service._extract_subfield(isbn_field, "a")
        isbn = MARC21Service._normalize_isbn(isbn_raw) if isbn_raw else None

        publication_year = MARC21Service._extract_publication_year(publication_field)
        edition = MARC21Service._extract_subfield(edition_field, "a")

        fingerprint_isbn = MARC21Service.hash_fingerprint(isbn) if isbn else None
        fingerprint_title_author = MARC21Service.hash_fingerprint(f"{title}|{'|'.join(authors)}")

        return {
            "title": title,
            "subtitle": subtitle,
            "isbn": isbn,
            "edition": edition,
            "publication_year": publication_year,
            "authors": authors,
            "subjects": subjects,
            "marc21_record": normalized,
            "fingerprint_isbn": fingerprint_isbn,
            "fingerprint_title_author": fingerprint_title_author,
        }

    @staticmethod
    def hash_fingerprint(value: str | None) -> str:
        return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    def _first_field(record: dict[str, Any], tag: str) -> dict[str, Any] | None:
        for field in record.get("fields", []):
            if field.get("tag") == tag:
                return field
        return None

    @staticmethod
    def _all_fields(record: dict[str, Any], tags: set[str]) -> list[dict[str, Any]]:
        return [field for field in record.get("fields", []) if field.get("tag") in tags]

    @staticmethod
    def _extract_subfield(field: dict[str, Any] | None, code: str) -> str | None:
        if not field:
            return None
        subfields = field.get("subfields") or {}
        value = subfields.get(code)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @staticmethod
    def _normalize_isbn(raw_isbn: str) -> str:
        return "".join(ch for ch in raw_isbn if ch.isdigit() or ch.lower() == "x")

    @staticmethod
    def _extract_publication_year(field: dict[str, Any] | None) -> int | None:
        if not field:
            return None

        for candidate in (
            MARC21Service._extract_subfield(field, "c"),
            MARC21Service._extract_subfield(field, "a"),
        ):
            if not candidate:
                continue
            digits = "".join(ch for ch in candidate if ch.isdigit())
            if len(digits) >= 4:
                return int(digits[:4])

        return None
