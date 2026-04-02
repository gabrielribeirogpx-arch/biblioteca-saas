from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LibraryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    is_active: bool


class LibraryListItem(LibraryResponse):
    tenant_id: int
    organization_id: int
    created_at: datetime


class CreateLibraryRequest(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    timezone: str = "America/Sao_Paulo"
    is_active: bool = True


class LibraryCreate(CreateLibraryRequest):
    pass


class LibraryUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


class LibraryPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    library_id: int
    max_loans: int
    loan_days: int
    fine_per_day: Decimal
    renewal_limit: int


class LibraryPolicyUpdate(BaseModel):
    max_loans: int = Field(ge=1, le=100)
    loan_days: int = Field(ge=1, le=365)
    fine_per_day: Decimal = Field(ge=0)
    renewal_limit: int = Field(ge=0, le=30)
