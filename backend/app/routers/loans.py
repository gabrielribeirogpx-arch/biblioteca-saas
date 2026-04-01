from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AuthContext,
    TenantScopedContext,
    get_current_user,
    get_db,
    get_tenant_context,
    require_librarian,
    require_user,
)
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.loans import LoanCreate, LoanListResponse, LoanOut, LoanRenewRequest
from app.services.audit_service import AuditService
from app.services.loans import LoanService

router = APIRouter()


@router.get("/", response_model=LoanListResponse, dependencies=[Depends(get_current_user)])
async def list_loans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> LoanListResponse:
    return await LoanService.list_loans(db, ctx.tenant.library_id, auth.tenant_id, page=page, page_size=page_size)


@router.post("/", response_model=LoanOut, dependencies=[Depends(get_current_user)])
async def create_loan(
    payload: LoanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_librarian),
) -> LoanOut:
    created = await LoanService.create_loan(db, payload, ctx.tenant.library_id, auth.tenant_id, ctx.user.id)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
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


@router.post("/{loan_id}/renew", response_model=LoanOut, dependencies=[Depends(get_current_user)])
async def renew_loan(
    loan_id: int,
    payload: LoanRenewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_librarian),
) -> LoanOut:
    renewed = await LoanService.renew_loan(db, ctx.tenant.library_id, auth.tenant_id, loan_id, payload.renewal_days)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
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


@router.post("/{loan_id}/return", response_model=LoanOut, dependencies=[Depends(get_current_user)])
async def return_loan(
    loan_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_librarian),
) -> LoanOut:
    returned = await LoanService.return_loan(db, ctx.tenant.library_id, auth.tenant_id, loan_id)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
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
