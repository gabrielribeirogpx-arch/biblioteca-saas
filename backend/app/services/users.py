from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.users import UserCreate, UserOut


class UserService:
    @staticmethod
    def create_user(db: AsyncSession, payload: UserCreate, tenant_id: str) -> UserOut:  # noqa: ARG004
        return UserOut(id=1, role="member", **payload.model_dump())

    @staticmethod
    def list_users(db: AsyncSession, tenant_id: str) -> list[UserOut]:  # noqa: ARG004
        return [UserOut(id=1, email="user@example.com", full_name="Demo User", role="member")]
