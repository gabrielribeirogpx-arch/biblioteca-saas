from datetime import date

from pydantic import BaseModel


class LoanCreate(BaseModel):
    copy_id: int
    due_date: date


class LoanOut(LoanCreate):
    id: int
    user_id: str
    status: str
