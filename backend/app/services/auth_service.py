from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.library import Library
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenPayload, TokenResponse
from app.services.audit_service import AuditService


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, password_hash: str) -> bool:
        return pwd_context.verify(plain_password, password_hash)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(payload: TokenPayload) -> str:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        exp = datetime.now(UTC) + expires_delta
        encoded = jwt.encode(
            {
                "sub": payload.sub,
                "role": payload.role.value,
                "library_id": payload.library_id,
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
            )
        except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc

    @staticmethod
    async def login(db: AsyncSession, payload: LoginRequest, tenant_id: str) -> TokenResponse:
        query = select(Library).where(Library.code == tenant_id)
        if tenant_id.isdigit():
            query = select(Library).where((Library.code == tenant_id) | (Library.id == int(tenant_id)))
        library = (await db.execute(query)).scalar_one_or_none()
        if not library:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        user = (
            await db.execute(
                select(User).where(
                    User.library_id == library.id,
                    User.email == payload.username,
                )
            )
        ).scalar_one_or_none()

        if not user or not user.is_active or not AuthService.verify_password(payload.password, user.password_hash):
            await AuditService.log_event(
                db=db,
                library_id=library.id,
                category=AuditCategory.AUTH,
                actor_type=AuditActorType.SYSTEM,
                actor_id=None,
                action="auth.login_failed",
                entity_type="user",
                entity_id=payload.username,
                summary="Failed login attempt",
                payload={"username": payload.username},
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token_payload = TokenPayload(sub=user.id, role=user.role, library_id=library.id)
        access_token = AuthService.create_access_token(token_payload)

        await AuditService.log_event(
            db=db,
            library_id=library.id,
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
