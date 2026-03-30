from pydantic import BaseModel


class SearchQuery(BaseModel):
    q: str


class SearchResult(BaseModel):
    id: str
    score: float
    title: str
