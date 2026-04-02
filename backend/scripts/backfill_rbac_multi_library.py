"""Backfill RBAC assignments and multi-library access.

Usage:
  python backend/scripts/backfill_rbac_multi_library.py --database-url postgresql+asyncpg://...
  python backend/scripts/backfill_rbac_multi_library.py --apply

By default, runs in dry-run mode.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "")

BACKFILL_USER_ROLES_SQL = text(
    """
    INSERT INTO user_roles (user_id, role_id, tenant_id, library_id)
    SELECT u.id, r.id, u.tenant_id, NULL::INTEGER
    FROM users u
    JOIN roles r
      ON r.tenant_id = u.tenant_id
     AND r.code = lower(u.role::text)
    WHERE u.tenant_id IS NOT NULL
    ON CONFLICT (user_id, role_id, library_id) DO NOTHING
    """
)

BACKFILL_USER_LIBRARIES_SQL = text(
    """
    INSERT INTO user_libraries (user_id, tenant_id, library_id)
    SELECT u.id, u.tenant_id, l.id
    FROM users u
    JOIN libraries l ON l.tenant_id = u.tenant_id
    WHERE u.tenant_id IS NOT NULL
    ON CONFLICT (user_id, library_id) DO NOTHING
    """
)

COUNT_USERS_WITHOUT_ROLES_SQL = text(
    """
    SELECT COUNT(*)
    FROM users u
    WHERE u.tenant_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1
        FROM user_roles ur
        WHERE ur.user_id = u.id
          AND ur.tenant_id = u.tenant_id
      )
    """
)

COUNT_USERS_WITHOUT_LIBRARIES_SQL = text(
    """
    SELECT COUNT(*)
    FROM users u
    WHERE u.tenant_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1
        FROM user_libraries ul
        WHERE ul.user_id = u.id
          AND ul.tenant_id = u.tenant_id
      )
    """
)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill RBAC and multi-library bindings")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Database connection URL")
    parser.add_argument("--apply", action="store_true", help="Apply correction (default is dry-run)")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required via --database-url or environment")

    engine = create_async_engine(args.database_url)
    try:
        async with engine.begin() as conn:
            users_without_roles = await conn.scalar(COUNT_USERS_WITHOUT_ROLES_SQL)
            users_without_libraries = await conn.scalar(COUNT_USERS_WITHOUT_LIBRARIES_SQL)

            print(f"Users without RBAC roles: {users_without_roles}")
            print(f"Users without library access grants: {users_without_libraries}")

            if not args.apply:
                print("Dry-run mode: no updates applied. Re-run with --apply to backfill.")
                return 1 if (users_without_roles or users_without_libraries) else 0

            user_roles_result = await conn.execute(BACKFILL_USER_ROLES_SQL)
            user_libraries_result = await conn.execute(BACKFILL_USER_LIBRARIES_SQL)

            users_without_roles_after = await conn.scalar(COUNT_USERS_WITHOUT_ROLES_SQL)
            users_without_libraries_after = await conn.scalar(COUNT_USERS_WITHOUT_LIBRARIES_SQL)

            print(f"Inserted user_roles rows: {user_roles_result.rowcount}")
            print(f"Inserted user_libraries rows: {user_libraries_result.rowcount}")
            print(f"Users without RBAC roles after backfill: {users_without_roles_after}")
            print(f"Users without library access grants after backfill: {users_without_libraries_after}")

            if users_without_roles_after or users_without_libraries_after:
                print("ERROR: Backfill incomplete. Inspect tenant data consistency.")
                return 2

            print("Backfill completed successfully.")
            return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
