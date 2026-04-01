from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.library import Library
from app.models.user import User
from app.schemas.libraries import LibraryListItem

router = APIRouter()


@router.get("", response_model=list[LibraryListItem], dependencies=[Depends(get_current_user)])
async def list_libraries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LibraryListItem]:
    result = await db.execute(
        select(Library)
        .join(User, User.library_id == Library.id)
        .where(
            User.email == current_user.email,
            User.tenant_id == current_user.tenant_id,
            User.is_active.is_(True),
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
