from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import Library
from app.models.user import User, UserRole
from app.schemas.tenants import TenantCreate
from app.services.auth_service import AuthService


DEFAULT_TENANT_CODE = "default"


class TenantService:
    @staticmethod
    async def seed_default_tenant(db: AsyncSession) -> Library:
        existing = (await db.execute(select(Library).where(Library.code == DEFAULT_TENANT_CODE))).scalar_one_or_none()
        if existing:
            return existing

        tenant = Library(name="Default", code=DEFAULT_TENANT_CODE, timezone="UTC")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        return tenant

    @staticmethod
    async def seed_default_admin(db: AsyncSession, tenant: Library) -> User:
        admin_email = "admin@admin.com"
        existing = (
            await db.execute(
                select(User).where(User.library_id == tenant.id, User.email == admin_email)
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        admin = User(
            library_id=tenant.id,
            email=admin_email,
            full_name="Admin",
            role=UserRole.SUPER_ADMIN,
            password_hash=AuthService.hash_password("123456"),
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return admin

    @staticmethod
    async def create_tenant(db: AsyncSession, payload: TenantCreate) -> Library:
        slug = payload.slug.strip().lower()
        name = payload.name.strip()
        if not slug or not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="slug and name are required")

        existing = (await db.execute(select(Library).where(Library.code == slug))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")

        tenant = Library(name=name, code=slug, timezone="UTC")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        return tenant
