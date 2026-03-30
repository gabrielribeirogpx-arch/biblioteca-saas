from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.loans import LoanCreate, LoanOut


class LoanService:
    @staticmethod
    def create_loan(db: AsyncSession, payload: LoanCreate, tenant_id: str, user_id: str) -> LoanOut:  # noqa: ARG004
        return LoanOut(id=1, user_id=user_id, status="active", **payload.model_dump())

    @staticmethod
    def list_loans(db: AsyncSession, tenant_id: str) -> list[LoanOut]:  # noqa: ARG004
        return [LoanOut(id=1, copy_id=1, due_date=date.today(), user_id="u1", status="active")]
