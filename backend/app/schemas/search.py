from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    q: str
    filters: dict[str, Any] = Field(default_factory=dict)
    must_terms: list[str] = Field(default_factory=list)
    should_terms: list[str] = Field(default_factory=list)
    must_not_terms: list[str] = Field(default_factory=list)
    autocomplete: bool = False


class SearchResult(BaseModel):
    id: str
    score: float
    title: str
