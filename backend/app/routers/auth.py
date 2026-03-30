from fastapi import APIRouter, Depends

from app.api.deps import TenantContext, resolve_tenant
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, tenant: TenantContext = Depends(resolve_tenant)) -> TokenResponse:
    return AuthService.login(payload, tenant.tenant_id)
