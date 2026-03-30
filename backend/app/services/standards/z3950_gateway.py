from __future__ import annotations

from typing import Any


class Z3950Gateway:
    """Simulated Z39.50 gateway adapter for external catalog lookups."""

    @staticmethod
    def lookup(query: str, limit: int = 5) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 25))
        term = query.strip() or "catalog"

        records: list[dict[str, Any]] = []
        for index in range(1, safe_limit + 1):
            records.append(
                {
                    "leader": "00000nam a2200000 i 4500",
                    "control_number": f"z3950-{term.lower().replace(' ', '-')}-{index}",
                    "fields": [
                        {
                            "tag": "020",
                            "ind1": " ",
                            "ind2": " ",
                            "subfields": {"a": f"9780000000{index:03d}"},
                        },
                        {
                            "tag": "100",
                            "ind1": "1",
                            "ind2": " ",
                            "subfields": {"a": f"Source Author {index}"},
                        },
                        {
                            "tag": "245",
                            "ind1": "1",
                            "ind2": "0",
                            "subfields": {
                                "a": f"{term.title()} Result {index}",
                                "b": "Imported from Z39.50",
                            },
                        },
                        {
                            "tag": "264",
                            "ind1": " ",
                            "ind2": "1",
                            "subfields": {"c": "2025"},
                        },
                        {
                            "tag": "650",
                            "ind1": " ",
                            "ind2": "0",
                            "subfields": {"a": term.title()},
                        },
                    ],
                }
            )

        return records
