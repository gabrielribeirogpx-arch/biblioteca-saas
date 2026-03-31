from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.users import UserCreate, UserOut
from app.services.auth_service import AuthService


class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, payload: UserCreate, library_id: int) -> UserOut:
        existing = (
            await db.execute(select(User).where(User.library_id == library_id, User.email == payload.email.strip().lower()))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

        user = User(
            library_id=library_id,
            email=payload.email.strip().lower(),
            full_name=payload.full_name.strip(),
            role=payload.role,
            password_hash=AuthService.hash_password(payload.password or "123456"),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role, password=None)

    @staticmethod
    async def list_users(db: AsyncSession, library_id: int) -> list[UserOut]:
        result = await db.execute(select(User).where(User.library_id == library_id).order_by(User.id.asc()))
        users = result.scalars().all()
        return [UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role, password=None) for user in users]
