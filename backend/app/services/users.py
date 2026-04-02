from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import Library
from app.models.rbac import Permission, Role, RolePermission, UserLibrary, UserRoleAssignment
from app.models.user import User
from app.schemas.users import LibraryAssignmentOut, RoleAssignmentOut, UserCreate, UserMetadataResponse, UserOut, UserUpdate
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService


class UserService:
    @staticmethod
    async def _get_tenant_libraries(db: AsyncSession, tenant_id: int, library_ids: Sequence[int]) -> list[Library]:
        if not library_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="User must have at least one library")

        unique_library_ids = list(dict.fromkeys(library_ids))
        libraries = (
            await db.execute(
                select(Library).where(
                    Library.tenant_id == tenant_id,
                    Library.id.in_(unique_library_ids),
                )
            )
        ).scalars().all()
        if len(libraries) != len(unique_library_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid library assignment for tenant")
        return libraries

    @staticmethod
    async def _get_tenant_roles(db: AsyncSession, tenant_id: int, role_ids: Sequence[int]) -> list[Role]:
        if not role_ids:
            return []
        unique_role_ids = list(dict.fromkeys(role_ids))
        roles = (
            await db.execute(
                select(Role).where(
                    Role.id.in_(unique_role_ids),
                    (Role.tenant_id.is_(None) | (Role.tenant_id == tenant_id)),
                )
            )
        ).scalars().all()
        if len(roles) != len(unique_role_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role assignment for tenant")
        return roles

    @staticmethod
    async def _build_user_out(db: AsyncSession, user: User) -> UserOut:
        libraries = (
            await db.execute(
                select(Library)
                .join(UserLibrary, UserLibrary.library_id == Library.id)
                .where(UserLibrary.user_id == user.id)
                .order_by(Library.name.asc())
            )
        ).scalars().all()

        roles = (
            await db.execute(
                select(Role)
                .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
                .where(UserRoleAssignment.user_id == user.id)
                .order_by(Role.name.asc())
            )
        ).scalars().all()

        role_ids = [role.id for role in roles]
        permission_rows: list[tuple[int, str]] = []
        if role_ids:
            permission_rows = (
                await db.execute(
                    select(RolePermission.role_id, Permission.code)
                    .join(Permission, Permission.id == RolePermission.permission_id)
                    .where(RolePermission.role_id.in_(role_ids))
                )
            ).all()

        role_permission_map: dict[int, set[str]] = {role.id: set() for role in roles}
        user_permissions: set[str] = set()
        for role_id, permission_code in permission_rows:
            role_permission_map[role_id].add(permission_code)
            user_permissions.add(permission_code)

        return UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            tenant_id=user.tenant_id,
            library_id=user.library_id,
            roles=[
                RoleAssignmentOut(
                    id=role.id,
                    code=role.code,
                    name=role.name,
                    permission_codes=sorted(role_permission_map.get(role.id, set())),
                )
                for role in roles
            ],
            libraries=[
                LibraryAssignmentOut(id=library.id, code=library.code, name=library.name)
                for library in libraries
            ],
            permissions=sorted(user_permissions),
        )

    @staticmethod
    async def assign_roles(db: AsyncSession, *, user: User, tenant_id: int, role_ids: list[int]) -> None:
        roles = await UserService._get_tenant_roles(db, tenant_id, role_ids)
        await db.execute(UserRoleAssignment.__table__.delete().where(UserRoleAssignment.user_id == user.id))
        for role in roles:
            db.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role_id=role.id,
                    tenant_id=tenant_id,
                    library_id=None,
                )
            )

    @staticmethod
    async def assign_libraries(db: AsyncSession, *, user: User, tenant_id: int, library_ids: list[int]) -> list[Library]:
        libraries = await UserService._get_tenant_libraries(db, tenant_id, library_ids)
        await db.execute(UserLibrary.__table__.delete().where(UserLibrary.user_id == user.id))
        for library in libraries:
            db.add(UserLibrary(user_id=user.id, tenant_id=tenant_id, library_id=library.id))
        return libraries

    @staticmethod
    async def create_user(db: AsyncSession, payload: UserCreate, tenant_id: int) -> UserOut:
        normalized_email = payload.email.strip().lower()
        existing = (
            await db.execute(select(User).where(User.tenant_id == tenant_id, User.email == normalized_email))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists in tenant")

        libraries = await UserService._get_tenant_libraries(db, tenant_id, payload.library_ids)
        primary_library = libraries[0]

        user = User(
            tenant_id=tenant_id,
            library_id=primary_library.id,
            email=normalized_email,
            full_name=payload.full_name.strip(),
            role=payload.role,
            password_hash=AuthService.hash_password(payload.password),
            is_active=payload.is_active,
        )
        db.add(user)
        await db.flush()

        await UserService.assign_libraries(db, user=user, tenant_id=tenant_id, library_ids=payload.library_ids)

        assigned_role_ids = payload.role_ids
        if not assigned_role_ids:
            default_role = (
                await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.code == payload.role.value))
            ).scalar_one_or_none()
            if default_role is not None:
                assigned_role_ids = [default_role.id]
        await UserService.assign_roles(db, user=user, tenant_id=tenant_id, role_ids=assigned_role_ids)
        await RBACService.ensure_user_bindings(db, user)

        await db.commit()
        await db.refresh(user)
        return await UserService._build_user_out(db, user)

    @staticmethod
    async def get_user(db: AsyncSession, *, tenant_id: int, library_id: int, user_id: int) -> UserOut:
        user = (
            await db.execute(
                select(User)
                .join(UserLibrary, UserLibrary.user_id == User.id)
                .where(
                    User.id == user_id,
                    User.tenant_id == tenant_id,
                    UserLibrary.library_id == library_id,
                )
            )
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return await UserService._build_user_out(db, user)

    @staticmethod
    async def update_user(
        db: AsyncSession,
        *,
        user_id: int,
        payload: UserUpdate,
        tenant_id: int,
        library_id: int,
    ) -> UserOut:
        user = (
            await db.execute(
                select(User)
                .join(UserLibrary, UserLibrary.user_id == User.id)
                .where(
                    User.id == user_id,
                    User.tenant_id == tenant_id,
                    UserLibrary.library_id == library_id,
                )
            )
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if payload.email is not None:
            normalized_email = payload.email.strip().lower()
            conflict = (
                await db.execute(
                    select(User).where(
                        User.tenant_id == tenant_id,
                        User.email == normalized_email,
                        User.id != user.id,
                    )
                )
            ).scalar_one_or_none()
            if conflict:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
            user.email = normalized_email

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.password is not None:
            user.password_hash = AuthService.hash_password(payload.password)
        if payload.role is not None:
            user.role = payload.role
        if payload.is_active is not None:
            user.is_active = payload.is_active

        if payload.library_ids is not None:
            libraries = await UserService.assign_libraries(db, user=user, tenant_id=tenant_id, library_ids=payload.library_ids)
            user.library_id = libraries[0].id

        if payload.role_ids is not None:
            await UserService.assign_roles(db, user=user, tenant_id=tenant_id, role_ids=payload.role_ids)

        await db.commit()
        await db.refresh(user)
        return await UserService._build_user_out(db, user)

    @staticmethod
    async def delete_user(db: AsyncSession, *, user_id: int, tenant_id: int, library_id: int) -> None:
        user = (
            await db.execute(
                select(User)
                .join(UserLibrary, UserLibrary.user_id == User.id)
                .where(
                    User.id == user_id,
                    User.tenant_id == tenant_id,
                    UserLibrary.library_id == library_id,
                )
            )
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await db.delete(user)
        await db.commit()

    @staticmethod
    async def list_users(db: AsyncSession, tenant_id: int, library_id: int, page: int = 1, page_size: int = 20) -> dict:
        offset = (page - 1) * page_size
        total = await db.scalar(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(UserLibrary, UserLibrary.user_id == User.id)
            .where(User.tenant_id == tenant_id, UserLibrary.library_id == library_id)
        )
        result = await db.execute(
            select(User)
            .join(UserLibrary, UserLibrary.user_id == User.id)
            .where(User.tenant_id == tenant_id, UserLibrary.library_id == library_id)
            .order_by(User.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        users = result.scalars().unique().all()

        items = [await UserService._build_user_out(db, user) for user in users]
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total or 0,
        }

    @staticmethod
    async def get_management_metadata(db: AsyncSession, *, tenant_id: int) -> UserMetadataResponse:
        roles = (await db.execute(select(Role).where((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None))))).scalars().all()
        libraries = (await db.execute(select(Library).where(Library.tenant_id == tenant_id).order_by(Library.name.asc()))).scalars().all()

        role_ids = [role.id for role in roles]
        permission_rows: list[tuple[int, str]] = []
        if role_ids:
            permission_rows = (
                await db.execute(
                    select(RolePermission.role_id, Permission.code)
                    .join(Permission, Permission.id == RolePermission.permission_id)
                    .where(RolePermission.role_id.in_(role_ids))
                )
            ).all()

        role_permission_map: dict[int, set[str]] = {role.id: set() for role in roles}
        for role_id, permission_code in permission_rows:
            role_permission_map[role_id].add(permission_code)

        return UserMetadataResponse(
            roles=[
                RoleAssignmentOut(
                    id=role.id,
                    code=role.code,
                    name=role.name,
                    permission_codes=sorted(role_permission_map.get(role.id, set())),
                )
                for role in sorted(roles, key=lambda value: value.name.lower())
            ],
            libraries=[LibraryAssignmentOut(id=library.id, code=library.code, name=library.name) for library in libraries],
        )
