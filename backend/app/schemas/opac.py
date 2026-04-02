from pydantic import BaseModel, Field


class OPACLibraryInfo(BaseModel):
    id: int
    name: str
    code: str
    tenant_id: int
    tenant_name: str
    tenant_slug: str


class OPACBookListItem(BaseModel):
    id: int
    title: str
    author: str
    isbn: str | None = None
    subjects: list[str] = Field(default_factory=list)
    cover_url: str | None = None
    available: bool
    total_copies: int
    available_copies: int
    status: str
    library: OPACLibraryInfo


class OPACBookListResponse(BaseModel):
    items: list[OPACBookListItem]
    page: int
    page_size: int
    total: int


class OPACHoldingLibrary(BaseModel):
    library: OPACLibraryInfo
    total_copies: int
    available_copies: int
    available: bool
    status: str


class OPACBookDetailResponse(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    author: str
    isbn: str | None = None
    subject: str | None = None
    subjects: list[str] = Field(default_factory=list)
    publication_year: int | None = None
    edition: str | None = None
    cover_url: str | None = None
    available: bool
    total_copies: int
    available_copies: int
    status: str
    library: OPACLibraryInfo
    libraries: list[OPACHoldingLibrary] = Field(default_factory=list)
