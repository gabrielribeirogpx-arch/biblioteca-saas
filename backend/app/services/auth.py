from app.schemas.auth import LoginRequest, TokenResponse


class AuthService:
    @staticmethod
    def login(payload: LoginRequest, tenant_id: str) -> TokenResponse:
        token = f"{tenant_id}:{payload.username}:token"
        return TokenResponse(access_token=token)
