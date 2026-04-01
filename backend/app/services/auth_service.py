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
from app.schemas.auth import LoginRequest, TokenPayload, TokenResponse
from app.services.audit_service import AuditService



class AuthService:
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def create_access_token(payload: TokenPayload) -> str:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        exp = datetime.now(timezone.utc) + expires_delta
        encoded = jwt.encode(
            {
                "sub": payload.sub,
                "role": payload.role.value,
                "library_id": payload.library_id,
                "tenant": payload.tenant,
                "exp": exp,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded

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
                library_id=int(decoded["library_id"]),
                tenant=str(decoded["tenant"]),
            )
        except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc

    @staticmethod
    async def login(db: AsyncSession, payload: LoginRequest, tenant: Library) -> TokenResponse:
        login_identifier = (payload.email or payload.username or "").strip().lower()
        if not login_identifier:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email is required")

        user = (
            await db.execute(
                select(User).where(
                    User.library_id == tenant.id,
                    User.email == login_identifier,
                )
            )
        ).scalar_one_or_none()

        print("LOGIN DEBUG:")
        print("email:", login_identifier)
        print("tenant:", getattr(tenant, "slug", tenant.code) if tenant else None)
        print("user encontrado:", user is not None)

        if not user or not user.is_active:
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
            library_id=tenant.id,
            tenant=tenant.code,
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

        return TokenResponse(access_token=access_token)
