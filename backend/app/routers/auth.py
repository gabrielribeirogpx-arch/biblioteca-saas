from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.library import Library
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    tenant = (
        request.headers.get("X-Tenant-ID")
        or request.headers.get("X-Tenant-Slug")
        or body.tenant
    )
    library_id = request.headers.get("X-Library-ID")
    if not tenant or not tenant.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant obrigatório")

    tenant = tenant.strip()
    query = select(Library).where(Library.code == tenant)
    if library_id and library_id.strip().isdigit():
        query = select(Library).where(Library.id == int(library_id.strip()))
    library = (await db.execute(query)).scalar_one_or_none()

    if not library:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant não encontrado")

    return await AuthService.login(db, body, library)
