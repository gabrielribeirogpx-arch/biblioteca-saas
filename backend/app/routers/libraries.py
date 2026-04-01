from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_current_user, get_db, require_admin
from app.models.library import Library
from app.schemas.libraries import LibraryCreate, LibraryListItem

router = APIRouter()


@router.post("", response_model=LibraryListItem)
async def create_library(
    payload: LibraryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    _auth: AuthContext = Depends(require_admin),
) -> LibraryListItem:
    normalized_code = payload.code.strip()
    normalized_name = payload.name.strip()

    if not normalized_code or not normalized_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name and code are required")

    source_library = (
        await db.execute(
            select(Library).where(
                Library.id == current_user.library_id,
                Library.tenant_id == current_user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if source_library is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Library access denied")

    library = Library(
        tenant_id=current_user.tenant_id,
        organization_id=source_library.organization_id,
        name=normalized_name,
        code=normalized_code,
    )
    db.add(library)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Library code already exists in tenant") from exc

    await db.refresh(library)
    return LibraryListItem(
        id=library.id,
        code=library.code,
        name=library.name,
        organization_id=library.organization_id,
    )


@router.get("", response_model=list[LibraryListItem], dependencies=[Depends(get_current_user)])
async def list_libraries(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[LibraryListItem]:
    result = await db.execute(
        select(Library)
        .where(
            Library.tenant_id == current_user.tenant_id,
        )
        .order_by(Library.name.asc())
    )
    libraries = result.scalars().all()
    return [
        LibraryListItem(
            id=library.id,
            code=library.code,
            name=library.name,
            organization_id=library.organization_id,
        )
        for library in libraries
    ]
