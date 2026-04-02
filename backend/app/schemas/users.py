from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: str
    full_name: str = Field(min_length=2, max_length=255)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.MEMBER
    role_ids: list[int] = Field(default_factory=list)
    library_ids: list[int] = Field(min_length=1)


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None
    role_ids: list[int] | None = None
    library_ids: list[int] | None = Field(default=None, min_length=1)


class RoleAssignmentOut(BaseModel):
    id: int
    code: str
    name: str
    permission_codes: list[str]


class LibraryAssignmentOut(BaseModel):
    id: int
    code: str
    name: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    tenant_id: int | None
    library_id: int
    roles: list[RoleAssignmentOut]
    libraries: list[LibraryAssignmentOut]
    permissions: list[str]


class UserListResponse(BaseModel):
    items: list[UserOut]
    page: int
    page_size: int
    total: int


class UserMetadataResponse(BaseModel):
    roles: list[RoleAssignmentOut]
    libraries: list[LibraryAssignmentOut]
