from app.schemas.reports import ReportSummary


class ReportService:
    @staticmethod
    def get_summary(tenant_id: str) -> ReportSummary:  # noqa: ARG004
        return ReportSummary(total_books=120, total_copies=320, active_loans=37)
