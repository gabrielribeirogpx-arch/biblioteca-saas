from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantContext, get_db, require_librarian, require_user, resolve_tenant
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.loans import LoanCreate, LoanOut, LoanRenewRequest
from app.services.audit_service import AuditService
from app.services.loans import LoanService

router = APIRouter()


@router.get("/", response_model=list[LoanOut])
async def list_loans(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_user),
) -> list[LoanOut]:
    return await LoanService.list_loans(db, tenant.library_id)


@router.post("/", response_model=LoanOut)
async def create_loan(
    payload: LoanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_librarian),
) -> LoanOut:
    created = await LoanService.create_loan(db, payload, tenant.library_id, auth.user_id)
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


@router.post("/{loan_id}/renew", response_model=LoanOut)
async def renew_loan(
    loan_id: int,
    payload: LoanRenewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_librarian),
) -> LoanOut:
    renewed = await LoanService.renew_loan(db, tenant.library_id, loan_id, payload.renewal_days)
    await AuditService.log_event(
        db=db,
        library_id=tenant.library_id,
        category=AuditCategory.CIRCULATION,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action="loans.renew",
        entity_type="loan",
        entity_id=str(loan_id),
        summary="Loan renewed",
        payload=payload.model_dump(mode="json"),
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return renewed


@router.post("/{loan_id}/return", response_model=LoanOut)
async def return_loan(
    loan_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_librarian),
) -> LoanOut:
    returned = await LoanService.return_loan(db, tenant.library_id, loan_id)
    await AuditService.log_event(
        db=db,
        library_id=tenant.library_id,
        category=AuditCategory.CIRCULATION,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action="loans.return",
        entity_type="loan",
        entity_id=str(loan_id),
        summary="Loan returned",
        payload=None,
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return returned
