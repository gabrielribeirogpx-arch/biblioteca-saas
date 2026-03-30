from fastapi import APIRouter, Depends

from app.api.deps import TenantContext, resolve_tenant
from app.schemas.reports import ReportSummary
from app.services.reports import ReportService

router = APIRouter()


@router.get("/summary", response_model=ReportSummary)
def report_summary(tenant: TenantContext = Depends(resolve_tenant)) -> ReportSummary:
    return ReportService.get_summary(tenant.tenant_id)
