from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
import logging

from fastapi import Depends, Header, HTTPException, Query, Request, status
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.library import Library
from app.models.user import User
from app.models.user import UserRole
from app.services.audit_service import AuditService
from app.services.rbac_service import RBACService


logger = logging.getLogger("app.request")


@dataclass(slots=True)
class TenantContext:
    tenant_id: int
    organization_id: int
    organization_slug: str
    library_id: int
    library_code: str


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


async def resolve_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_library_id: str | None = Header(default=None, alias="X-Library-ID"),
    tenant: str | None = Query(default=None),
) -> TenantContext:
    forwarded_host = request.headers.get("x-forwarded-host", "")
    host_header = forwarded_host.split(",")[0].strip() if forwarded_host else request.headers.get("host", "")
    host_value = (host_header or "").strip().lower().rstrip(".")
    if host_value.count(":") == 1:
        host_value = host_value.split(":", 1)[0]

    tenant_slug: str | None = None
    tenant_query = (tenant or "").strip().lower()
    if tenant_query:
        tenant_slug = tenant_query

    host_parts = [part for part in host_value.split(".") if part]
    if not tenant_slug and len(host_parts) >= 3:
        tenant_slug = host_parts[0]

    is_dev_host = host_value in {"localhost", "127.0.0.1", "0.0.0.0"} or host_value.endswith(".localhost")
    if not tenant_slug and is_dev_host:
        dev_tenant = request.query_params.get("tenant")
        if dev_tenant and dev_tenant.strip():
            tenant_slug = dev_tenant.strip().lower()

    if tenant_slug:
        library = (
            await db.execute(
                select(Library)
                .options(selectinload(Library.organization))
                .options(selectinload(Library.tenant))
                .join(Library.tenant)
                .where(Library.is_active.is_(True), Library.tenant.has(slug=tenant_slug))
                .order_by(Library.id.asc())
            )
        ).scalars().first()
        if not library:
            detail = "Tenant not found"
            if tenant_query:
                detail = "Tenant not found for query parameter"
            elif host_value:
                detail = "Tenant not found for host"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

        tenant_context = TenantContext(
            tenant_id=library.tenant_id,
            organization_id=library.organization_id,
            organization_slug=library.organization.slug,
            library_id=library.id,
            library_code=library.code,
        )
        request.state.tenant_context = tenant_context
        logger.info(
            "tenant.resolve host success tenant=%s slug=%s library_id=%s",
            tenant_context.tenant_id,
            tenant_slug,
            tenant_context.library_id,
        )
        return tenant_context

    if request.url.path.startswith("/api/public/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant query parameter is required")

    if x_library_id and x_library_id.strip().isdigit():
        library = (
            await db.execute(
                select(Library)
                .options(selectinload(Library.organization))
                .options(selectinload(Library.tenant))
                .where(Library.id == int(x_library_id.strip()))
            )
        ).scalar_one_or_none()
    else:
        library = (
            await db.execute(
                select(Library)
                .options(selectinload(Library.organization))
                .options(selectinload(Library.tenant))
                .order_by(Library.id.asc())
            )
        ).scalars().first()

    if not library:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No library available")

    tenant_context = TenantContext(
        tenant_id=library.tenant_id,
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


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")

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

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from None

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    token_tenant_id = payload.get("tenant_id")
    if token_tenant_id is not None and user.tenant_id is not None:
        if int(token_tenant_id) != int(user.tenant_id):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant mismatch")

    return user


async def get_request_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(resolve_tenant),
    x_library_id: str | None = Header(default=None, alias="X-Library-ID"),
) -> TenantScopedContext:
    effective_tenant_id = current_user.tenant_id or tenant_context.tenant_id
    if current_user.tenant_id is not None and tenant_context.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    requested_library_id = x_library_id or request.query_params.get("library_id")
    library_id: int | None = None
    if requested_library_id is not None:
        normalized_library_id = requested_library_id.strip()
        if not normalized_library_id.isdigit():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid library_id")
        library_id = int(normalized_library_id)
    elif tenant_context.tenant_id == effective_tenant_id:
        library_id = tenant_context.library_id

    if library_id is not None:
        library = (
            await db.execute(
                select(Library)
                .options(selectinload(Library.organization))
                .options(selectinload(Library.tenant))
                .where(
                    Library.id == library_id,
                    Library.tenant_id == effective_tenant_id,
                )
            )
        ).scalar_one_or_none()
    else:
        library = None

    if library is None:
        library = (
            await db.execute(
                select(Library)
                .options(selectinload(Library.organization))
                .options(selectinload(Library.tenant))
                .where(
                    Library.tenant_id == effective_tenant_id,
                    Library.is_active.is_(True),
                )
                .order_by(Library.id.asc())
            )
        ).scalars().first()

    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library não encontrada")

    if not await RBACService.user_has_library_access(db=db, user=current_user, library_id=library.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso à biblioteca negado")

    resolved_tenant_context = TenantContext(
        tenant_id=library.tenant_id,
        organization_id=library.organization_id,
        organization_slug=library.organization.slug,
        library_id=library.id,
        library_code=library.code,
    )
    request.state.tenant_context = resolved_tenant_context
    return TenantScopedContext(user=current_user, tenant=resolved_tenant_context)


async def get_current_library(
    context: TenantScopedContext = Depends(get_request_context),
) -> TenantContext:
    return context.tenant


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
    context: TenantScopedContext = Depends(get_request_context),
) -> TenantScopedContext:
    return context


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


def require_permission(permission_code: str) -> Callable[..., User]:
    async def dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        context: TenantScopedContext = Depends(get_tenant_context),
    ) -> User:
        current_user = context.user
        has_permission = await RBACService.user_has_permission(
            db=db,
            user_id=current_user.id,
            permission_code=permission_code,
            tenant_id=context.tenant.tenant_id,
            library_id=context.tenant.library_id,
            fallback_role=current_user.role,
        )
        if not has_permission:
            await AuditService.log_event(
                db=db,
                organization_id=context.tenant.organization_id,
                library_id=context.tenant.library_id,
                tenant_id=context.tenant.tenant_id,
                category=AuditCategory.SECURITY,
                actor_type=AuditActorType.USER,
                actor_id=current_user.id,
                action="rbac.permission_denied",
                entity_type="permission",
                entity_id=permission_code,
                summary="Permission denied by permission guard",
                payload={"permission_code": permission_code},
                request_id=request.headers.get("x-request-id"),
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        return current_user

    return dependency
