from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_db_session, resolve_tenant
from app.schemas.books import BookCreate, BookOut
from app.services.books import BookService

router = APIRouter()


@router.get("/", response_model=list[BookOut])
def list_books(
    db: Session = Depends(get_db_session),
    tenant: TenantContext = Depends(resolve_tenant),
) -> list[BookOut]:
    return BookService.list_books(db, tenant.tenant_id)


@router.post("/", response_model=BookOut)
def create_book(
    payload: BookCreate,
    db: Session = Depends(get_db_session),
    tenant: TenantContext = Depends(resolve_tenant),
) -> BookOut:
    return BookService.create_book(db, payload, tenant.tenant_id)
