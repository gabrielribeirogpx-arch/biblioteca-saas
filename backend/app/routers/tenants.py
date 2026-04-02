from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_db, require_admin, resolve_tenant
from app.models.user import User
from app.schemas.tenants import TenantCreate, TenantOut
from app.services.tenant_service import TenantService

router = APIRouter()


@router.post("", response_model=TenantOut)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _tenant: TenantContext = Depends(resolve_tenant),
    _auth: User = Depends(require_admin),
) -> TenantOut:
    created = await TenantService.create_tenant(db, payload)
    return TenantOut(id=created.id, slug=created.code, name=created.name)
