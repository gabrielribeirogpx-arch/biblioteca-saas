from app.schemas.search import SearchResult


class SearchService:
    @staticmethod
    def search_books(tenant_id: str, query: str) -> list[SearchResult]:
        return [SearchResult(id=f"{tenant_id}:book:1", score=0.99, title=f"Match for '{query}'")]
