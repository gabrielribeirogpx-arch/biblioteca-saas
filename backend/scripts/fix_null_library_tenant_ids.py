"""Detect and repair libraries with NULL tenant_id.

Usage:
  python backend/scripts/fix_null_library_tenant_ids.py --database-url postgresql+asyncpg://...
  python backend/scripts/fix_null_library_tenant_ids.py --apply

By default, runs in dry-run mode and only reports rows.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "")

DETECT_NULL_SQL = text(
    """
    SELECT l.id, l.code, l.name, l.organization_id
    FROM libraries AS l
    WHERE l.tenant_id IS NULL
    ORDER BY l.id ASC
    """
)

REPAIR_SQL = text(
    """
    UPDATE libraries AS l
    SET tenant_id = t.id
    FROM organizations AS o
    JOIN tenants AS t ON t.slug = o.slug
    WHERE l.tenant_id IS NULL
      AND l.organization_id = o.id
    """
)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Fix libraries with NULL tenant_id")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Database connection URL")
    parser.add_argument("--apply", action="store_true", help="Apply correction (default is dry-run)")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required via --database-url or environment")

    engine = create_async_engine(args.database_url)
    try:
        async with engine.begin() as conn:
            rows = (await conn.execute(DETECT_NULL_SQL)).mappings().all()

            if not rows:
                print("No libraries with NULL tenant_id found.")
                return 0

            print(f"Found {len(rows)} libraries with NULL tenant_id:")
            for row in rows:
                print(
                    f"  - library_id={row['id']} code={row['code']} name={row['name']} organization_id={row['organization_id']}"
                )

            if not args.apply:
                print("Dry-run mode: no updates applied. Re-run with --apply to fix.")
                return 1

            result = await conn.execute(REPAIR_SQL)
            print(f"Updated rows: {result.rowcount}")

            remaining = (await conn.execute(DETECT_NULL_SQL)).mappings().all()
            if remaining:
                print("ERROR: Some libraries still have NULL tenant_id after repair.")
                for row in remaining:
                    print(f"  - unresolved library_id={row['id']} organization_id={row['organization_id']}")
                return 2

            print("Repair completed successfully.")
            return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
