from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
import logging

from fastapi import Depends, Header, HTTPException, Request, status
import jwt
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.library import Library
from app.models.organization import Organization
from app.models.user import User
from app.models.user import UserRole
from app.services.audit_service import AuditService


DEFAULT_TENANT_CODE = "default"
logger = logging.getLogger("app.request")


@dataclass(slots=True)
class TenantContext:
    tenant_id: str
    organization_id: int
    organization_slug: str
    library_id: int
    library_code: str


async def _resolve_library_from_tenant_key(db: AsyncSession, tenant_key: str) -> Library | None:
    def _build_query():
        return (
            select(Library)
            .options(selectinload(Library.organization))
            .where(Library.code == tenant_key)
        )

    try:
        library = (await db.execute(_build_query())).scalar_one_or_none()
    except ProgrammingError as exc:
        error_message = str(getattr(exc, "orig", exc)).lower()
        if "libraries.is_active" not in error_message and "is_active" not in error_message:
            raise
        await db.rollback()
        await db.execute(text("ALTER TABLE libraries ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
        await db.commit()
        library = (await db.execute(_build_query())).scalar_one_or_none()

    if library:
        return library

    organization = (await db.execute(select(Organization).where(Organization.slug == tenant_key))).scalar_one_or_none()
    if not organization:
        return None

    return (
        await db.execute(
            select(Library)
            .options(selectinload(Library.organization))
            .where(Library.organization_id == organization.id)
            .order_by(Library.id.asc())
        )
    ).scalars().first()


@dataclass(slots=True)
class TenantScopedContext:
    user: "User"
    tenant: TenantContext


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is temporarily unavailable.",
        )

    async with AsyncSessionLocal() as db:
        yield db


def _extract_subdomain(host: str | None) -> str | None:
    if not host:
        return None

    hostname = host.split(":", 1)[0].strip().lower()
    if not hostname:
        return None

    parts = hostname.split(".")

    if hostname.endswith(".localhost") and len(parts) >= 2:
        return parts[0]

    if len(parts) >= 3:
        return parts[0]

    return None


async def resolve_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    x_library_id: str | None = Header(default=None, alias="X-Library-ID"),
    tenant_query: str | None = None,
) -> TenantContext:
    tenant_key = (
        x_tenant_slug
        or x_tenant_id
        or tenant_query
        or _extract_subdomain(request.headers.get("host"))
        or DEFAULT_TENANT_CODE
    ).strip()
    logger.info("tenant.resolve requested tenant_key=%s", tenant_key)

    library = await _resolve_library_from_tenant_key(db, tenant_key)
    if not library and tenant_key != DEFAULT_TENANT_CODE:
        logger.warning("tenant.resolve miss for tenant_key=%s; attempting fallback=%s", tenant_key, DEFAULT_TENANT_CODE)
        library = await _resolve_library_from_tenant_key(db, DEFAULT_TENANT_CODE)

    if not library:
        logger.error("tenant.resolve failed; default tenant unavailable")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Default tenant is unavailable")

    if x_library_id and x_library_id.strip().isdigit():
        forced_library = (
            await db.execute(
                select(Library)
                .options(selectinload(Library.organization))
                .where(Library.id == int(x_library_id.strip()))
            )
        ).scalar_one_or_none()
        if forced_library and forced_library.tenant_id == library.tenant_id:
            library = forced_library

    tenant_context = TenantContext(
        tenant_id=library.code,
        organization_id=library.organization_id,
        organization_slug=library.organization.slug,
        library_id=library.id,
        library_code=library.code,
    )
    request.state.tenant_context = tenant_context
    logger.info(
        "tenant.resolve success tenant=%s organization_id=%s library_id=%s",
        tenant_context.tenant_id,
        tenant_context.organization_id,
        tenant_context.library_id,
    )
    return tenant_context


async def get_tenant_from_request(request: Request, db: AsyncSession) -> Library | None:
    tenant_key = (
        request.headers.get("X-Tenant-Slug")
        or request.headers.get("X-Tenant-ID")
    )
    if not tenant_key:
        return None

    tenant_key = tenant_key.strip()
    if not tenant_key:
        return None

    return await _resolve_library_from_tenant_key(db, tenant_key)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    header_tenant_slug = request.headers.get("X-Tenant-Slug")
    header_tenant_id = request.headers.get("X-Tenant-ID")

    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth header")
    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")

    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from None

    user_id = payload.get("sub")

    print("payload:", payload)
    print("user_id:", user_id)

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from None

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    print("user:", user)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    if header_tenant_slug:
        tenant_library = await _resolve_library_from_tenant_key(db, header_tenant_slug.strip())
        if tenant_library and tenant_library.tenant_id != user.tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant mismatch")

    if header_tenant_id and header_tenant_id.strip().isdigit() and user.tenant_id is not None:
        if int(header_tenant_id.strip()) != int(user.tenant_id):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant mismatch")

    return user


async def get_current_library(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_library_id: str | None = Header(default=None, alias="X-Library-ID"),
) -> TenantContext:
    if not x_library_id or not x_library_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Library-ID header is required")
    if not x_library_id.strip().isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Library-ID header")

    library_id = int(x_library_id.strip())
    library = (
        await db.execute(
            select(Library)
            .options(selectinload(Library.organization))
            .where(
                Library.id == library_id,
                Library.tenant_id == current_user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Library access denied")

    tenant_context = TenantContext(
        tenant_id=library.organization.slug,
        organization_id=library.organization_id,
        organization_slug=library.organization.slug,
        library_id=library.id,
        library_code=library.code,
    )
    request.state.tenant_context = tenant_context
    return tenant_context


async def get_current_tenant(
    current_library: TenantContext = Depends(get_current_library),
    user=Depends(get_current_user),
) -> TenantContext:
    tenant_context = current_library
    logger.info(
        "tenant.current success tenant=%s organization_id=%s library_id=%s user_id=%s",
        tenant_context.tenant_id,
        tenant_context.organization_id,
        tenant_context.library_id,
        user.id,
    )
    return tenant_context


async def resolve_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_library),
) -> TenantScopedContext:
    user = (
        await db.execute(
            select(User).where(
                User.email == current_user.email,
                User.library_id == tenant.library_id,
                User.tenant_id == current_user.tenant_id,
                User.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Library access denied")
    if user.role != current_user.role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Library role mismatch")

    request.state.tenant_context = tenant
    return TenantScopedContext(user=user, tenant=tenant)


async def get_tenant_context(
    context: TenantScopedContext = Depends(resolve_context),
) -> TenantScopedContext:
    return context


def role_guard(*allowed_roles: UserRole) -> Callable[..., User]:
    async def dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            tenant = getattr(request.state, "tenant_context", None)
            if tenant is not None:
                await AuditService.log_event(
                    db=db,
                    organization_id=tenant.organization_id,
                    library_id=tenant.library_id,
                    category=AuditCategory.SECURITY,
                    actor_type=AuditActorType.USER,
                    actor_id=current_user.id,
                    action="rbac.permission_denied",
                    entity_type="route",
                    entity_id=f"{request.method} {request.url.path}",
                    summary="Permission denied by role guard",
                    payload={
                        "required_roles": [role.value for role in allowed_roles],
                        "actual_role": current_user.role.value,
                    },
                    request_id=request.headers.get("x-request-id"),
                    ip_address=request.client.host if request.client else None,
                )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        return current_user

    return dependency


require_admin = role_guard(UserRole.SUPER_ADMIN)
require_librarian = role_guard(UserRole.SUPER_ADMIN, UserRole.LIBRARIAN)
require_user = role_guard(
    UserRole.SUPER_ADMIN,
    UserRole.LIBRARIAN,
    UserRole.ASSISTANT,
    UserRole.MEMBER,
)
