from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_db_session, resolve_tenant
from app.schemas.users import UserCreate, UserOut
from app.services.users import UserService

router = APIRouter()


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db_session),
    tenant: TenantContext = Depends(resolve_tenant),
) -> list[UserOut]:
    return UserService.list_users(db, tenant.tenant_id)


@router.post("/", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db_session),
    tenant: TenantContext = Depends(resolve_tenant),
) -> UserOut:
    return UserService.create_user(db, payload, tenant.tenant_id)
