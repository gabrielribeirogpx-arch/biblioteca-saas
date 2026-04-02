from __future__ import annotations

import logging

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission, Role, RolePermission, UserLibrary, UserRoleAssignment
from app.models.user import User, UserRole


logger = logging.getLogger("app.request")

LEGACY_ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPER_ADMIN: {
        "books.read",
        "books.create",
        "books.update",
        "books.delete",
        "users.read",
        "users.create",
        "users.update",
        "users.delete",
        "libraries.switch",
    },
    UserRole.LIBRARIAN: {"books.read", "books.create", "books.update", "users.read", "libraries.switch"},
    UserRole.ASSISTANT: {"books.read", "users.read", "libraries.switch"},
    UserRole.MEMBER: {"books.read"},
}


class RBACService:
    @staticmethod
    def _is_missing_relation_error(exc: Exception) -> bool:
        root = getattr(exc, "orig", exc)
        sqlstate = getattr(root, "sqlstate", None) or getattr(root, "pgcode", None)
        if sqlstate == "42P01":
            return True
        return "does not exist" in str(root).lower() and (
            "user_roles" in str(root).lower()
            or "user_libraries" in str(root).lower()
            or "roles" in str(root).lower()
            or "permissions" in str(root).lower()
        )

    @staticmethod
    async def get_user_permission_codes(
        db: AsyncSession,
        user_id: int,
        tenant_id: int | None,
        library_id: int | None,
        fallback_role: UserRole | None = None,
    ) -> set[str]:
        fallback_permissions = set(LEGACY_ROLE_PERMISSIONS.get(fallback_role, set()))
        if tenant_id is None:
            return fallback_permissions

        query = (
            select(Permission.code)
            .select_from(UserRoleAssignment)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.tenant_id == tenant_id,
                or_(UserRoleAssignment.library_id.is_(None), UserRoleAssignment.library_id == library_id),
                or_(Role.tenant_id.is_(None), Role.tenant_id == tenant_id),
                or_(Role.library_id.is_(None), Role.library_id == library_id),
            )
            .distinct()
        )
        try:
            permission_codes = set((await db.execute(query)).scalars().all())
        except (ProgrammingError, DBAPIError) as exc:
            if RBACService._is_missing_relation_error(exc):
                logger.warning("rbac fallback activated due to missing RBAC tables: %s", exc)
                return fallback_permissions
            raise

        if permission_codes:
            return permission_codes

        return fallback_permissions

    @staticmethod
    async def user_has_permission(
        db: AsyncSession,
        user_id: int,
        permission_code: str,
        tenant_id: int | None,
        library_id: int | None,
        fallback_role: UserRole | None = None,
    ) -> bool:
        if fallback_role == UserRole.SUPER_ADMIN:
            return True
        permission_codes = await RBACService.get_user_permission_codes(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            library_id=library_id,
            fallback_role=fallback_role,
        )
        return permission_code in permission_codes

    @staticmethod
    async def user_has_library_access(
        db: AsyncSession,
        user: User,
        library_id: int,
    ) -> bool:
        if user.tenant_id is None:
            return False

        if user.library_id == library_id:
            return True

        try:
            explicit_access = (
                await db.execute(
                    select(UserLibrary.id).where(
                        UserLibrary.user_id == user.id,
                        UserLibrary.tenant_id == user.tenant_id,
                        UserLibrary.library_id == library_id,
                    )
                )
            ).scalar_one_or_none()
            if explicit_access is not None:
                return True

            # Backward-compatible fallback: if user has no explicit library grants yet,
            # allow access to all tenant libraries (legacy behavior).
            has_any_explicit_grants = (
                await db.execute(
                    select(UserLibrary.id).where(
                        and_(
                            UserLibrary.user_id == user.id,
                            UserLibrary.tenant_id == user.tenant_id,
                        )
                    )
                )
            ).scalar_one_or_none()
            return has_any_explicit_grants is None
        except (ProgrammingError, DBAPIError) as exc:
            if RBACService._is_missing_relation_error(exc):
                logger.warning("rbac library-access fallback activated due to missing tables: %s", exc)
                return True
            raise

    @staticmethod
    async def ensure_user_bindings(db: AsyncSession, user: User) -> None:
        if user.tenant_id is None:
            return

        try:
            user_library_exists = (
                await db.execute(
                    select(UserLibrary.id).where(
                        UserLibrary.user_id == user.id,
                        UserLibrary.library_id == user.library_id,
                    )
                )
            ).scalar_one_or_none()
            if user_library_exists is None:
                db.add(UserLibrary(user_id=user.id, tenant_id=user.tenant_id, library_id=user.library_id))

            role = (
                await db.execute(
                    select(Role).where(
                        Role.tenant_id == user.tenant_id,
                        Role.code == user.role.value,
                    )
                )
            ).scalar_one_or_none()
            if role is None:
                role = Role(
                    tenant_id=user.tenant_id,
                    code=user.role.value,
                    name=user.role.value.replace("_", " ").title(),
                    description="Auto-provisioned role from legacy user role",
                    is_system=True,
                )
                db.add(role)
                await db.flush()

            assignment_exists = (
                await db.execute(
                    select(UserRoleAssignment.id).where(
                        UserRoleAssignment.user_id == user.id,
                        UserRoleAssignment.role_id == role.id,
                        UserRoleAssignment.tenant_id == user.tenant_id,
                        UserRoleAssignment.library_id.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if assignment_exists is None:
                db.add(
                    UserRoleAssignment(
                        user_id=user.id,
                        role_id=role.id,
                        tenant_id=user.tenant_id,
                        library_id=None,
                    )
                )
        except (ProgrammingError, DBAPIError) as exc:
            if RBACService._is_missing_relation_error(exc):
                logger.warning("rbac binding bootstrap skipped because tables are missing: %s", exc)
                return
            raise
