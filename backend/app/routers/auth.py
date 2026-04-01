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
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    tenant_key = (
        request.headers.get("X-Tenant-Slug")
        or request.headers.get("X-Tenant-ID")
        or request.query_params.get("tenant")
    )
    if not tenant_key or not tenant_key.strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant = (
        await db.execute(
            select(Library).where(Library.code == tenant_key.strip())
        )
    ).scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return await AuthService.login(db, payload, tenant)
