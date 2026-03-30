from pydantic import BaseModel

from app.models.user import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPayload(BaseModel):
    sub: int
    role: UserRole
    library_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
