from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantContext, get_db, require_librarian, require_user, resolve_tenant
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.loans import LoanCreate, LoanOut
from app.services.audit_service import AuditService
from app.services.loans import LoanService

router = APIRouter()


@router.get("/", response_model=list[LoanOut])
async def list_loans(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_user),
) -> list[LoanOut]:
    return LoanService.list_loans(db, tenant.tenant_id)


@router.post("/", response_model=LoanOut)
async def create_loan(
    payload: LoanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_librarian),
) -> LoanOut:
    created = LoanService.create_loan(db, payload, tenant.tenant_id, str(auth.user_id))
    await AuditService.log_event(
        db=db,
        library_id=tenant.library_id,
        category=AuditCategory.CIRCULATION,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action="loans.create",
        entity_type="loan",
        entity_id=str(created.id),
        summary="Loan created",
        payload=payload.model_dump(mode="json"),
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return created
