from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.library import Library
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginUser, TokenPayload, TokenResponse
from app.services.audit_service import AuditService


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas


class AuthService:
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except (TypeError, ValueError):
            return False

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def create_access_token(payload: TokenPayload) -> str:
        to_encode = {
            # RFC 7519 expects "sub" as a string. PyJWT validates this claim type on decode.
            "sub": str(payload.sub),
            "role": payload.role.value,
            "tenant_id": payload.tenant_id,
            "library_id": payload.library_id,
            "tenant": payload.tenant,
            "organization_id": payload.organization_id,
        }

        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
        })

        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> TokenPayload:
        try:
            decoded = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return TokenPayload(
                sub=int(decoded["sub"]),
                role=decoded["role"],
                tenant_id=int(decoded["tenant_id"]),
                library_id=int(decoded["library_id"]),
                tenant=str(decoded["tenant"]),
                organization_id=int(decoded["organization_id"]) if decoded.get("organization_id") is not None else None,
            )
        except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc

    @staticmethod
    async def login(db: AsyncSession, payload: LoginRequest, tenant: Library) -> TokenResponse:
        try:
            login_identifier = (payload.email or payload.username or "").strip().lower()
            if not login_identifier:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email is required")

            user = (
                await db.execute(
                    select(User).where(
                        User.tenant_id == tenant.tenant_id,
                        User.email == login_identifier,
                    )
                )
            ).scalar_one_or_none()

            print("Tenant:", tenant.id)
            print("User:", user)

            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

            if not user.is_active:
                await AuditService.log_event(
                    db=db,
                    library_id=tenant.id,
                    category=AuditCategory.AUTH,
                    actor_type=AuditActorType.SYSTEM,
                    actor_id=None,
                    action="auth.login_failed",
                    entity_type="user",
                    entity_id=login_identifier,
                    summary="Failed login attempt",
                    payload={"email": login_identifier},
                )
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

            hashed_password = getattr(user, "hashed_password", user.password_hash)
            if not AuthService.verify_password(payload.password, hashed_password):
                await AuditService.log_event(
                    db=db,
                    library_id=tenant.id,
                    category=AuditCategory.AUTH,
                    actor_type=AuditActorType.SYSTEM,
                    actor_id=None,
                    action="auth.login_failed",
                    entity_type="user",
                    entity_id=login_identifier,
                    summary="Failed login attempt",
                    payload={"email": login_identifier},
                )
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

            token_payload = TokenPayload(
                sub=user.id,
                role=user.role,
                library_id=user.library_id or tenant.id,
                tenant_id=user.tenant_id or tenant.tenant_id or tenant.organization_id,
                tenant=tenant.code,
                organization_id=tenant.organization_id,
            )
            access_token = AuthService.create_access_token(token_payload)

            await AuditService.log_event(
                db=db,
                library_id=tenant.id,
                category=AuditCategory.AUTH,
                actor_type=AuditActorType.USER,
                actor_id=user.id,
                action="auth.login_success",
                entity_type="user",
                entity_id=str(user.id),
                summary="User logged in",
                payload={"email": user.email, "role": user.role.value},
            )

            return TokenResponse(
                access_token=access_token,
                user=LoginUser(id=user.id, email=user.email, role=user.role),
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Falha no processo de autenticação",
            ) from exc
