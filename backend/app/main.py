from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, books, copies, loans, reports, search, users


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://front-biblioteca-saas.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🚀 FastAPI started")
print("CORS middleware loaded")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(books.router, prefix="/api/v1/books", tags=["books"])
app.include_router(copies.router, prefix="/api/v1/copies", tags=["copies"])
app.include_router(loans.router, prefix="/api/v1/loans", tags=["loans"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
