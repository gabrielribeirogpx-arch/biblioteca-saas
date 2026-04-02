from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.library import Library
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, SwitchLibraryRequest, TokenPayload, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        library_id = request.headers.get("X-Library-ID")
        query = select(Library).options(selectinload(Library.tenant)).order_by(Library.id.asc())
        if library_id and library_id.strip().isdigit():
            query = query.where(Library.id == int(library_id.strip()))
        elif body.tenant and body.tenant.strip().isdigit():
            query = query.where(Library.tenant_id == int(body.tenant.strip()))
        library = (await db.execute(query)).scalars().first()

        if not library:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Biblioteca não encontrada")

        return await AuthService.login(db, body, library)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requisição de login inválida",
        ) from exc


@router.post("/switch-library", response_model=AccessTokenResponse)
async def switch_library(
    body: SwitchLibraryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccessTokenResponse:
    library = (
        await db.execute(
            select(Library)
            .options(selectinload(Library.tenant))
            .where(
                Library.id == body.library_id,
                Library.tenant_id == current_user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Library access denied")

    token_payload = TokenPayload(
        sub=current_user.id,
        tenant_id=current_user.tenant_id or library.tenant_id,
        tenant=str(current_user.tenant_id or library.tenant_id),
        library_id=library.id,
        role=current_user.role,
        organization_id=library.organization_id,
    )
    access_token = AuthService.create_access_token(token_payload)
    return AccessTokenResponse(access_token=access_token)
