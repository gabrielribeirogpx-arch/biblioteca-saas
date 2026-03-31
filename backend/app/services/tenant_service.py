from __future__ import annotations

import logging
import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import Library
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, RegisterResponse, TokenPayload
from app.schemas.tenants import TenantCreate
from app.services.auth_service import AuthService


DEFAULT_TENANT_CODE = "default"
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
logger = logging.getLogger(__name__)


class TenantService:
    @staticmethod
    def normalize_slug(raw_slug: str) -> str:
        normalized = unicodedata.normalize("NFKD", raw_slug).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower().strip()
        normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
        normalized = re.sub(r"[\s_-]+", "-", normalized)
        normalized = re.sub(r"-+", "-", normalized).strip("-")
        return normalized

    @staticmethod
    def normalize_email(raw_email: str) -> str:
        return raw_email.strip().lower()

    @staticmethod
    def sanitize_name(raw_name: str) -> str:
        return re.sub(r"\s+", " ", raw_name).strip()

    @staticmethod
    def validate_password_strength(password: str) -> None:
        has_upper = any(char.isupper() for char in password)
        has_lower = any(char.islower() for char in password)
        has_digit = any(char.isdigit() for char in password)
        has_special = any(char in PASSWORD_SPECIAL_CHARS for char in password)

        if len(password) < 8 or not (has_upper and has_lower and has_digit and has_special):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Password must contain at least 8 characters, including upper/lower case, "
                    "number, and special character"
                ),
            )

    @staticmethod
    async def is_slug_available(db: AsyncSession, slug: str) -> bool:
        existing = (await db.execute(select(Library).where(Library.code == slug))).scalar_one_or_none()
        return existing is None

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
        slug = TenantService.normalize_slug(payload.slug)
        name = TenantService.sanitize_name(payload.name)
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

    @staticmethod
    async def register_tenant_admin(db: AsyncSession, payload: RegisterRequest) -> RegisterResponse:
        tenant_name = TenantService.sanitize_name(payload.name)
        tenant_slug = TenantService.normalize_slug(payload.slug)
        email = TenantService.normalize_email(payload.email)
        password = payload.password.strip()

        if not tenant_name or not tenant_slug:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name and slug are required")

        TenantService.validate_password_strength(password)

        existing_tenant = (await db.execute(select(Library).where(Library.code == tenant_slug))).scalar_one_or_none()
        if existing_tenant:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant slug already exists")

        try:
            tenant = Library(name=tenant_name, code=tenant_slug, timezone="UTC")
            db.add(tenant)
            await db.flush()

            existing_email = (
                await db.execute(select(User).where(User.library_id == tenant.id, User.email == email))
            ).scalar_one_or_none()
            if existing_email:
                await db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists for this tenant")

            admin_user = User(
                library_id=tenant.id,
                email=email,
                full_name=tenant_name,
                role=UserRole.SUPER_ADMIN,
                password_hash=AuthService.hash_password(password),
                is_active=True,
            )
            db.add(admin_user)
            await db.flush()
            await db.commit()

            token = AuthService.create_access_token(
                TokenPayload(sub=admin_user.id, role=admin_user.role, library_id=tenant.id)
            )
            return RegisterResponse(success=True, tenant_slug=tenant_slug, token=token)
        except HTTPException:
            raise
        except IntegrityError as exc:
            await db.rollback()
            logger.exception("Failed to register tenant admin due to database integrity error")
            error_message = str(exc.orig).lower() if exc.orig else str(exc).lower()
            if "libraries_code_key" in error_message or "uq" in error_message and "slug" in error_message:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant slug already exists") from exc
            if "uq_users_library_email" in error_message or "users" in error_message and "email" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists for this tenant",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to create account with provided data",
            ) from exc
        except Exception as exc:
            await db.rollback()
            logger.exception("Unexpected error while registering tenant admin")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to create account. Please check your data and try again",
            ) from exc
