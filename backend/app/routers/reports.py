from fastapi import APIRouter, Depends, Query
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantScopedContext, get_db, get_tenant_context, require_admin
from app.schemas.reports import (
    MostBorrowedItem,
    OverdueItem,
    PerformanceMetrics,
    ReportSummary,
    TenantReportBundle,
    UsageReport,
)
from app.services.reports import ReportService

router = APIRouter()
logger = logging.getLogger("app.request")


@router.get("/summary", response_model=ReportSummary)
async def report_summary(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_admin),
) -> ReportSummary:
    logger.info(
        "reports.summary context tenant=%s organization_id=%s library_id=%s user_id=%s",
        ctx.tenant.tenant_id,
        ctx.tenant.organization_id,
        ctx.tenant.library_id,
        auth.user_id,
    )
    return await ReportService.get_summary(db, ctx.tenant.library_id, ctx.tenant.tenant_id)


@router.get("/most-borrowed", response_model=list[MostBorrowedItem])
async def report_most_borrowed(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_admin),
) -> list[MostBorrowedItem]:
    return await ReportService.most_borrowed(db, ctx.tenant.library_id, limit)


@router.get("/overdue", response_model=list[OverdueItem])
async def report_overdue(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_admin),
) -> list[OverdueItem]:
    return await ReportService.overdue_items(db, ctx.tenant.library_id, limit)


@router.get("/usage", response_model=UsageReport)
async def report_usage(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_admin),
) -> UsageReport:
    return await ReportService.usage_metrics(db, ctx.tenant.library_id)


@router.get("/performance", response_model=PerformanceMetrics)
async def report_performance(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_admin),
) -> PerformanceMetrics:
    return await ReportService.performance_metrics(db, ctx.tenant.library_id)


@router.get("/bundle", response_model=TenantReportBundle)
async def report_bundle(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_admin),
) -> TenantReportBundle:
    return await ReportService.tenant_bundle(db, ctx.tenant.library_id, ctx.tenant.tenant_id)
