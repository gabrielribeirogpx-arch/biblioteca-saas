from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_db, resolve_tenant
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
) -> TokenResponse:
    return await AuthService.login(db, payload, tenant.tenant_id)
