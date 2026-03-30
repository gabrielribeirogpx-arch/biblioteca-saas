from collections.abc import Generator
from dataclasses import dataclass

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


@dataclass(slots=True)
class TenantContext:
    tenant_id: str


@dataclass(slots=True)
class AuthContext:
    user_id: str
    role: str


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def resolve_tenant(x_tenant_id: str | None = Header(default=None)) -> TenantContext:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required X-Tenant-ID header",
        )

    return TenantContext(tenant_id=x_tenant_id)


def get_auth_context(
    x_user_id: str | None = Header(default=None),
    x_user_role: str = Header(default="member"),
) -> AuthContext:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-User-ID header",
        )

    return AuthContext(user_id=x_user_id, role=x_user_role)
