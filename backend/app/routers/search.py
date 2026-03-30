from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, TenantContext, require_user, resolve_tenant
from app.schemas.search import SearchQuery, SearchResult
from app.services.search import SearchService

router = APIRouter()


@router.post("/books", response_model=list[SearchResult])
async def search_books(
    payload: SearchQuery,
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_user),
) -> list[SearchResult]:
    return SearchService.search_books(tenant.tenant_id, payload.q)
