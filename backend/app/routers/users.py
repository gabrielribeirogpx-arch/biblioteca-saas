from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, TenantScopedContext, get_db, get_tenant_context, require_admin, require_user
from app.models.audit_log import AuditActorType, AuditCategory
from app.schemas.users import UserCreate, UserOut
from app.services.audit_service import AuditService
from app.services.users import UserService

router = APIRouter()


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_user),
) -> list[UserOut]:
    return await UserService.list_users(db, ctx.tenant.library_id)


@router.post("/", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: AuthContext = Depends(require_admin),
) -> UserOut:
    created = await UserService.create_user(db, payload, ctx.tenant.library_id)
    await AuditService.log_event(
        db=db,
        library_id=ctx.tenant.library_id,
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
