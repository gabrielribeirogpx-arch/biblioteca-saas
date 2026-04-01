from app.models.user import UserRole

from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str | None = None
    role: UserRole = UserRole.MEMBER


class UserOut(UserCreate):
    id: int
    role: UserRole
    password: str | None = None


class UserListResponse(BaseModel):
    items: list[UserOut]
    page: int
    page_size: int
    total: int
