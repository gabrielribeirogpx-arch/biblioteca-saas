from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantContext, get_db, require_admin, require_user, resolve_tenant
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.users import UserCreate, UserOut
from app.services.audit_service import AuditService
from app.services.users import UserService

router = APIRouter()


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_user),
) -> list[UserOut]:
    return UserService.list_users(db, tenant.tenant_id)


@router.post("/", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(resolve_tenant),
    auth: AuthContext = Depends(require_admin),
) -> UserOut:
    created = UserService.create_user(db, payload, tenant.tenant_id)
    await AuditService.log_event(
        db=db,
        library_id=tenant.library_id,
        category=AuditCategory.SECURITY,
        actor_type=AuditActorType.USER,
        actor_id=auth.user_id,
        action="users.create",
        entity_type="user",
        entity_id=str(created.id),
        summary="User created",
        payload={"email": created.email, "role": created.role},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return created
