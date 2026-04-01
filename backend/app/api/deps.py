from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.library import Library
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService


DEFAULT_TENANT_CODE = "default"


@dataclass(slots=True)
class TenantContext:
    tenant_id: str
    library_id: int
    library_code: str


@dataclass(slots=True)
class AuthContext:
    user_id: int
    role: UserRole
    library_id: int


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
    tenant_query: str | None = None,
) -> TenantContext:
    tenant_query = tenant_query or request.query_params.get("tenant")
    tenant_key = (
        x_tenant_slug
        or x_tenant_id
        or tenant_query
        or _extract_subdomain(request.headers.get("host"))
        or DEFAULT_TENANT_CODE
    ).strip()

    query = select(Library).where(Library.code == tenant_key)
    if tenant_key.isdigit():
        query = select(Library).where((Library.code == tenant_key) | (Library.id == int(tenant_key)))

    library = (await db.execute(query)).scalar_one_or_none()
    if not library and tenant_key != DEFAULT_TENANT_CODE:
        library = (
            await db.execute(select(Library).where(Library.code == DEFAULT_TENANT_CODE))
        ).scalar_one_or_none()

    if not library:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Default tenant is unavailable")

    tenant_context = TenantContext(
        tenant_id=library.code,
        library_id=library.id,
        library_code=library.code,
    )
    request.state.tenant_context = tenant_context
    return tenant_context


async def get_tenant_from_request(request: Request, db: AsyncSession) -> Library | None:
    tenant_key = (
        request.headers.get("X-Tenant-Slug")
        or request.headers.get("X-Tenant-ID")
        or request.query_params.get("tenant")
    )
    if not tenant_key:
        return None

    tenant_key = tenant_key.strip()
    if not tenant_key:
        return None

    query = select(Library).where(Library.code == tenant_key)
    if tenant_key.isdigit():
        query = select(Library).where((Library.code == tenant_key) | (Library.id == int(tenant_key)))

    return (await db.execute(query)).scalar_one_or_none()


_bearer = HTTPBearer(auto_error=False)


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthContext:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    payload: TokenPayload = AuthService.decode_access_token(credentials.credentials)
    tenant_slug = request.headers.get("X-Tenant-Slug") or request.headers.get("X-Tenant-ID")
    if not tenant_slug:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant header is required")

    tenant_slug = tenant_slug.strip()
    if payload.tenant != tenant_slug:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant inválido")

    auth_context = AuthContext(
        user_id=payload.sub,
        role=payload.role,
        library_id=payload.library_id,
    )
    request.state.auth_context = auth_context
    return auth_context


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    auth_header = request.headers.get("Authorization")
    tenant_slug = (
        request.headers.get("X-Tenant-Slug")
        or request.headers.get("X-Tenant-ID")
        or request.query_params.get("tenant")
    )

    print("AUTH HEADER:", auth_header)
    print("TENANT:", tenant_slug)

    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth header")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")

    token = auth_header.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        print("PAYLOAD:", payload)
    except Exception as e:
        print("JWT ERROR:", str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from None

    user_id = payload.get("sub")
    token_tenant = payload.get("tenant")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if tenant_slug:
        tenant_slug = tenant_slug.strip()
    elif token_tenant:
        tenant_slug = str(token_tenant).strip()

    if not tenant_slug:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    if token_tenant and str(token_tenant).strip() != tenant_slug:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant mismatch")

    tenant = (
        await db.execute(
            select(Library).where(Library.code == tenant_slug)
        )
    ).scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant não encontrado")

    user = (
        await db.execute(
            select(User)
            .where(
                User.id == user_id,
                User.library_id == tenant.id,
            )
        )
    ).scalar_one_or_none()

    print("USER FOUND:", user)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    return user


async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    user=Depends(get_current_user),
) -> TenantContext:
    tenant_query = request.query_params.get("tenant")
    tenant_key = (x_tenant_slug or x_tenant_id or tenant_query or str(user.library_id)).strip()

    query = select(Library).where(Library.code == tenant_key)
    if tenant_key.isdigit():
        query = select(Library).where((Library.code == tenant_key) | (Library.id == int(tenant_key)))

    library = (await db.execute(query)).scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant_context = TenantContext(
        tenant_id=library.code,
        library_id=library.id,
        library_code=library.code,
    )
    request.state.tenant_context = tenant_context
    return tenant_context


async def get_tenant_context(
    user=Depends(get_current_user),
    tenant: TenantContext = Depends(get_current_tenant),
) -> TenantScopedContext:
    if tenant.library_id != user.library_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tenant mismatch")
    return TenantScopedContext(user=user, tenant=tenant)


def role_guard(*allowed_roles: UserRole) -> Callable[..., AuthContext]:
    async def dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        auth: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        if auth.role not in allowed_roles:
            tenant = getattr(request.state, "tenant_context", None)
            if tenant is not None:
                await AuditService.log_event(
                    db=db,
                    library_id=tenant.library_id,
                    category=AuditCategory.SECURITY,
                    actor_type=AuditActorType.USER,
                    actor_id=auth.user_id,
                    action="rbac.permission_denied",
                    entity_type="route",
                    entity_id=f"{request.method} {request.url.path}",
                    summary="Permission denied by role guard",
                    payload={
                        "required_roles": [role.value for role in allowed_roles],
                        "actual_role": auth.role.value,
                    },
                    request_id=request.headers.get("x-request-id"),
                    ip_address=request.client.host if request.client else None,
                )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        request.state.auth_context = auth
        return auth

    return dependency


require_admin = role_guard(UserRole.SUPER_ADMIN)
require_librarian = role_guard(UserRole.SUPER_ADMIN, UserRole.LIBRARIAN)
require_user = role_guard(
    UserRole.SUPER_ADMIN,
    UserRole.LIBRARIAN,
    UserRole.ASSISTANT,
    UserRole.MEMBER,
)
