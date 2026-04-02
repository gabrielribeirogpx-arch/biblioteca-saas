from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantScopedContext, get_db, get_tenant_context, require_permission
from app.models.audit_log import AuditActorType, AuditCategory
from app.models.user import User
from app.schemas.users import UserCreate, UserListResponse, UserMetadataResponse, UserOut, UserUpdate
from app.services.audit_service import AuditService
from app.services.users import UserService

router = APIRouter()


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    _: User = Depends(require_permission("users.read")),
) -> UserListResponse:
    return await UserService.list_users(
        db,
        tenant_id=ctx.tenant.tenant_id,
        library_id=ctx.tenant.library_id,
        page=page,
        page_size=page_size,
    )


@router.get("/metadata", response_model=UserMetadataResponse)
async def users_metadata(
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    _: User = Depends(require_permission("users.read")),
) -> UserMetadataResponse:
    return await UserService.get_management_metadata(db, tenant_id=ctx.tenant.tenant_id)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    _: User = Depends(require_permission("users.read")),
) -> UserOut:
    return await UserService.get_user(
        db,
        tenant_id=ctx.tenant.tenant_id,
        library_id=ctx.tenant.library_id,
        user_id=user_id,
    )


@router.post("/", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_permission("users.create")),
) -> UserOut:
    created = await UserService.create_user(db, payload, tenant_id=ctx.tenant.tenant_id)
    await AuditService.log_event(
        db=db,
        organization_id=ctx.tenant.organization_id,
        tenant_id=ctx.tenant.tenant_id,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.SECURITY,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="CREATE_USER",
        entity_type="user",
        entity_id=str(created.id),
        summary="User created",
        payload={"email": created.email, "role": created.role.value, "libraries": [library.id for library in created.libraries]},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return created


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_permission("users.update")),
) -> UserOut:
    updated = await UserService.update_user(
        db,
        user_id=user_id,
        payload=payload,
        tenant_id=ctx.tenant.tenant_id,
        library_id=ctx.tenant.library_id,
    )
    await AuditService.log_event(
        db=db,
        organization_id=ctx.tenant.organization_id,
        tenant_id=ctx.tenant.tenant_id,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.SECURITY,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="UPDATE_USER",
        entity_type="user",
        entity_id=str(updated.id),
        summary="User updated",
        payload={"email": updated.email, "role": updated.role.value, "libraries": [library.id for library in updated.libraries]},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantScopedContext = Depends(get_tenant_context),
    auth: User = Depends(require_permission("users.delete")),
) -> Response:
    await UserService.delete_user(
        db,
        user_id=user_id,
        tenant_id=ctx.tenant.tenant_id,
        library_id=ctx.tenant.library_id,
    )
    await AuditService.log_event(
        db=db,
        organization_id=ctx.tenant.organization_id,
        tenant_id=ctx.tenant.tenant_id,
        library_id=ctx.tenant.library_id,
        category=AuditCategory.SECURITY,
        actor_type=AuditActorType.USER,
        actor_id=auth.id,
        action="DELETE_USER",
        entity_type="user",
        entity_id=str(user_id),
        summary="User deleted",
        payload={"deleted_user_id": user_id},
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
