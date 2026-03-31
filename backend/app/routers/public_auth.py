from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.auth import RegisterRequest, RegisterResponse, SlugAvailabilityResponse
from app.services.tenant_service import TenantService

router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    return await TenantService.register_tenant_admin(db, payload)


@router.get("/slug-availability", response_model=SlugAvailabilityResponse)
async def slug_availability(
    slug: str = Query(min_length=1, max_length=64),
    db: AsyncSession = Depends(get_db),
) -> SlugAvailabilityResponse:
    normalized_slug = TenantService.normalize_slug(slug)
    available = await TenantService.is_slug_available(db, normalized_slug)
    return SlugAvailabilityResponse(slug=normalized_slug, available=available)
