from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
import traceback
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.organization import Organization
from app.routers import authorities, auth, books, catalog, copies, fines, libraries, loans, public_auth, public_books, reports, reservations, search, tenants, users
from app.services.tenant_service import TenantService


logger = logging.getLogger("app.request")


def _run_db_migrations() -> None:
    alembic_ini_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    has_organization_migration = any("organization" in file.name for file in versions_dir.glob("*.py"))
    if not has_organization_migration:
        command.revision(
            alembic_cfg,
            message="add organizations table",
            autogenerate=True,
        )
        logger.info("Generated missing organizations migration automatically")

    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations applied up to head")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        _run_db_migrations()
    except Exception:
        logger.exception("Failed to run database migrations during startup; continuing without crashing")

    if AsyncSessionLocal is not None:
        async with AsyncSessionLocal() as db:
            try:
                await db.execute(text("SELECT 1 FROM organizations LIMIT 1"))
            except SQLAlchemyError:
                logger.warning("Skipping default seeding because organizations table is not available")
                await db.rollback()
            else:
                try:
                    # Guard query: skip startup seeding gracefully if Organization access fails.
                    await db.execute(text(f"SELECT 1 FROM {Organization.__tablename__} LIMIT 1"))
                    default_tenant = await TenantService.seed_default_tenant(db)
                    await TenantService.seed_default_admin(db, default_tenant)
                except SQLAlchemyError:
                    logger.warning("Skipping default seeding because Organization query failed")
                    await db.rollback()
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        print("🔥 ERRO NÃO TRATADO:")
        traceback.print_exc()
        raise e


class RequestContextLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            tenant_context = getattr(request.state, "tenant_context", None)
            auth_context = getattr(request.state, "auth_context", None)
            logger.exception(
                json.dumps(
                    {
                        "request_id": request_id,
                        "tenant_id": getattr(tenant_context, "tenant_id", None),
                        "organization_id": getattr(tenant_context, "organization_id", None),
                        "library_id": getattr(tenant_context, "library_id", None),
                        "user_id": getattr(auth_context, "user_id", None),
                        "endpoint": f"{request.method} {request.url.path}",
                        "status_code": 500,
                    }
                )
            )
            response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
        else:
            tenant_context = getattr(request.state, "tenant_context", None)
            auth_context = getattr(request.state, "auth_context", None)
            logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "tenant_id": getattr(tenant_context, "tenant_id", None),
                        "organization_id": getattr(tenant_context, "organization_id", None),
                        "library_id": getattr(tenant_context, "library_id", None),
                        "user_id": getattr(auth_context, "user_id", None),
                        "endpoint": f"{request.method} {request.url.path}",
                        "status_code": response.status_code,
                    }
                )
            )
        response.headers["x-request-id"] = request_id
        return response


app.add_middleware(RequestContextLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(public_auth.router, prefix="/api/public", tags=["public-auth"])
app.include_router(public_books.router, prefix="/api/public", tags=["public-books"])
app.include_router(books.router, prefix="/api/v1/books", tags=["books"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
app.include_router(copies.router, prefix="/api/v1/copies", tags=["copies"])
app.include_router(loans.router, prefix="/api/v1/loans", tags=["loans"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(reservations.router, prefix="/api/v1/reservations", tags=["reservations"])
app.include_router(fines.router, prefix="/api/v1/fines", tags=["fines"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
app.include_router(libraries.router, prefix="/api/v1/libraries", tags=["libraries"])
app.include_router(authorities.router, prefix="/api/v1", tags=["authorities"])


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
