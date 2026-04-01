from pydantic import BaseModel


class LibraryListItem(BaseModel):
    id: int
    code: str
    name: str
    organization_id: int
