from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantContext, get_auth_context, get_db, resolve_tenant
from app.schemas.loans import LoanCreate, LoanOut
from app.services.loans import LoanService

router = APIRouter()


@router.get("/", response_model=list[LoanOut])
def list_loans(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
) -> list[LoanOut]:
    return LoanService.list_loans(db, tenant.tenant_id)


@router.post("/", response_model=LoanOut)
def create_loan(
    payload: LoanCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(get_auth_context),
) -> LoanOut:
    return LoanService.create_loan(db, payload, tenant.tenant_id, auth.user_id)
