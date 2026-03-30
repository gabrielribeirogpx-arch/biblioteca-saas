from fastapi import APIRouter, Depends

from app.api.deps import TenantContext, resolve_tenant
from app.schemas.search import SearchQuery, SearchResult
from app.services.search import SearchService

router = APIRouter()


@router.post("/books", response_model=list[SearchResult])
def search_books(payload: SearchQuery, tenant: TenantContext = Depends(resolve_tenant)) -> list[SearchResult]:
    return SearchService.search_books(tenant.tenant_id, payload.q)
