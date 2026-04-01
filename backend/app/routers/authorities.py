from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.authorities import AuthorityCreateRequest, AuthorityItem
from app.services.authorities import AuthorityService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/authors", response_model=list[AuthorityItem])
async def list_authors(
    q: str = "",
    db: AsyncSession = Depends(get_db),
) -> list[AuthorityItem]:
    authors = await AuthorityService.list_authors(db, q)
    return [AuthorityItem(id=author.id, name=author.name) for author in authors]


@router.post("/authors", response_model=AuthorityItem)
async def create_author(
    payload: AuthorityCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthorityItem:
    author = await AuthorityService.get_or_create_author(db, payload.name)
    await db.commit()
    return AuthorityItem(id=author.id, name=author.name)


@router.get("/subjects", response_model=list[AuthorityItem])
async def list_subjects(
    q: str = "",
    db: AsyncSession = Depends(get_db),
) -> list[AuthorityItem]:
    subjects = await AuthorityService.list_subjects(db, q)
    return [AuthorityItem(id=subject.id, name=subject.name) for subject in subjects]


@router.post("/subjects", response_model=AuthorityItem)
async def create_subject(
    payload: AuthorityCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthorityItem:
    subject = await AuthorityService.get_or_create_subject(db, payload.name)
    await db.commit()
    return AuthorityItem(id=subject.id, name=subject.name)
