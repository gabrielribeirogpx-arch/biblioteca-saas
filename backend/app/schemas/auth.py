from pydantic import BaseModel, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str


class TokenPayload(BaseModel):
    sub: int
    role: UserRole
    library_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    success: bool
    tenant_slug: str
    token: str | None = None


class SlugAvailabilityResponse(BaseModel):
    slug: str
    available: bool
