from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, books, copies, loans, reports, search, users


def create_app() -> FastAPI:
    application = FastAPI(
        title="Library SaaS API",
        description="Multi-tenant enterprise-grade library management API",
        version="1.0.0",
    )

    origins = [
        "https://front-biblioteca-saas.vercel.app",
        "http://localhost:3000",
    ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    application.include_router(books.router, prefix="/api/v1/books", tags=["books"])
    application.include_router(copies.router, prefix="/api/v1/copies", tags=["copies"])
    application.include_router(loans.router, prefix="/api/v1/loans", tags=["loans"])
    application.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    application.include_router(search.router, prefix="/api/v1/search", tags=["search"])
    application.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

    @application.get("/", tags=["health"])
    def root() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
