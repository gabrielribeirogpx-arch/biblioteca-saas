from __future__ import annotations

import base64
import json
from typing import Any


class ISO2709Codec:
    """Lightweight ISO 2709-like codec for MARC byte stream transport."""

    @staticmethod
    def encode(record: dict[str, Any]) -> bytes:
        payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        return payload.encode("utf-8")

    @staticmethod
    def decode(payload: bytes) -> dict[str, Any]:
        return json.loads(payload.decode("utf-8"))

    @staticmethod
    def encode_base64(record: dict[str, Any]) -> str:
        return base64.b64encode(ISO2709Codec.encode(record)).decode("ascii")

    @staticmethod
    def decode_base64(payload_base64: str) -> dict[str, Any]:
        return ISO2709Codec.decode(base64.b64decode(payload_base64.encode("ascii")))
