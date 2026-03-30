from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    full_name: str


class UserOut(UserCreate):
    id: int
    role: str
