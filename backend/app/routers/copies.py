from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_db, resolve_tenant
from app.schemas.copies import CopyCreate, CopyOut
from app.services.copies import CopyService

router = APIRouter()


@router.get("/", response_model=list[CopyOut])
def list_copies(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
) -> list[CopyOut]:
    return CopyService.list_copies(db, tenant.tenant_id)


@router.post("/", response_model=CopyOut)
def create_copy(
    payload: CopyCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
) -> CopyOut:
    return CopyService.create_copy(db, payload, tenant.tenant_id)
