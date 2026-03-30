from __future__ import annotations

from typing import Any

from app.services.standards.marc21_service import MARC21Service


class AACR2Validator:
    """Validation rules aligned with practical AACR2 cataloging checks."""

    @staticmethod
    def validate(record: dict[str, Any]) -> tuple[bool, list[str]]:
        normalized = MARC21Service.normalize_record(record)
        errors: list[str] = []

        title = AACR2Validator._extract_subfield(normalized, "245", "a")
        if not title:
            errors.append("Field 245$a (title proper) is required.")

        main_author = AACR2Validator._extract_subfield(normalized, "100", "a")
        if not main_author:
            errors.append("Field 100$a (main entry - personal name) is required.")

        isbn = AACR2Validator._extract_subfield(normalized, "020", "a")
        if isbn:
            normalized_isbn = "".join(ch for ch in isbn if ch.isdigit() or ch.lower() == "x")
            if len(normalized_isbn) not in {10, 13}:
                errors.append("Field 020$a must contain a valid ISBN-10 or ISBN-13.")

        for field in normalized.get("fields", []):
            tag = field.get("tag", "")
            if len(tag) != 3 or not tag.isdigit():
                errors.append(f"Field tag '{tag}' must be a 3-digit numeric MARC tag.")

        return (len(errors) == 0, errors)

    @staticmethod
    def _extract_subfield(record: dict[str, Any], tag: str, code: str) -> str | None:
        for field in record.get("fields", []):
            if field.get("tag") == tag:
                subfields = field.get("subfields") or {}
                value = subfields.get(code)
                if isinstance(value, list):
                    return value[0] if value else None
                return value
        return None
