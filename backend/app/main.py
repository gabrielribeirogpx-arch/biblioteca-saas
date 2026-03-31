from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.routers import auth, books, copies, loans, reports, search, tenants, users
from app.services.tenant_service import TenantService


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if AsyncSessionLocal is not None:
        async with AsyncSessionLocal() as db:
            await TenantService.seed_default_tenant(db)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(books.router, prefix="/api/v1/books", tags=["books"])
app.include_router(copies.router, prefix="/api/v1/copies", tags=["copies"])
app.include_router(loans.router, prefix="/api/v1/loans", tags=["loans"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(tenants.router, prefix="/tenants", tags=["tenants"])


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
