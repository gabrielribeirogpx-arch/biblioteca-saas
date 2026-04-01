from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.routers import auth, books, catalog, copies, fines, loans, public_auth, reports, reservations, search, tenants, users
from app.services.tenant_service import TenantService


logger = logging.getLogger("app.request")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if AsyncSessionLocal is not None:
        async with AsyncSessionLocal() as db:
            default_tenant = await TenantService.seed_default_tenant(db)
            await TenantService.seed_default_admin(db, default_tenant)
    yield


app = FastAPI(lifespan=lifespan)


class RequestContextLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        tenant_context = getattr(request.state, "tenant_context", None)
        auth_context = getattr(request.state, "auth_context", None)
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "tenant_id": getattr(tenant_context, "library_id", None),
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


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
