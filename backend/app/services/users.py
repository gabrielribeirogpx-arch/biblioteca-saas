from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import Library
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
        library = (await db.execute(select(Library).where(Library.id == library_id))).scalar_one_or_none()
        if library is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")

        user = User(
            tenant_id=library.tenant_id,
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
    async def list_users(db: AsyncSession, library_id: int, page: int = 1, page_size: int = 20) -> dict:
        offset = (page - 1) * page_size
        total = await db.scalar(select(func.count()).select_from(User).where(User.library_id == library_id))
        result = await db.execute(
            select(User).where(User.library_id == library_id).order_by(User.id.asc()).offset(offset).limit(page_size)
        )
        users = result.scalars().all()
        return {
            "items": [UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role, password=None) for user in users],
            "page": page,
            "page_size": page_size,
            "total": total or 0,
        }
