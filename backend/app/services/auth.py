from app.models.user import UserRole
from app.schemas.auth import LoginRequest, LoginUser, TokenResponse


class AuthService:
    @staticmethod
    def login(payload: LoginRequest, tenant_id: str) -> TokenResponse:
        token = f"{tenant_id}:{payload.username}:token"
        return TokenResponse(
            access_token=token,
            user=LoginUser(
                id=0,
                email=payload.email or payload.username or "",
                role=UserRole.MEMBER,
            ),
        )
