from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_current_user, get_db, require_admin
from app.models.library import Library
from app.models.library_policy import LibraryPolicy
from app.schemas.libraries import (
    CreateLibraryRequest,
    LibraryListItem,
    LibraryPolicyRead,
    LibraryPolicyUpdate,
    LibraryUpdate,
)
from app.services.library_service import LibraryService

router = APIRouter()


def _assert_library_tenant_scope(library: Library, expected_tenant_id: int) -> None:
    if library.tenant_id != expected_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security violation: cross-tenant library leakage detected",
        )


async def _get_tenant_library_or_404(db: AsyncSession, library_id: int, tenant_id: int) -> Library:
    library = (
        await db.execute(
            select(Library).where(
                Library.id == library_id,
                Library.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
    _assert_library_tenant_scope(library, tenant_id)
    return library


@router.post("", response_model=LibraryListItem)
async def create_library(
    payload: CreateLibraryRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    _auth: AuthContext = Depends(require_admin),
) -> LibraryListItem:
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

    _assert_library_tenant_scope(source_library, current_user.tenant_id)

    library = await LibraryService.create_library(
        db,
        tenant_id=current_user.tenant_id,
        organization_id=source_library.organization_id,
        name=payload.name,
        code=payload.code,
        timezone=payload.timezone,
        is_active=payload.is_active,
    )
    _assert_library_tenant_scope(library, current_user.tenant_id)

    return LibraryListItem.model_validate(library)


@router.get("", response_model=list[LibraryListItem], dependencies=[Depends(get_current_user)])
async def list_libraries(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[LibraryListItem]:
    libraries = await LibraryService.list_libraries(db, tenant_id=current_user.tenant_id)

    for library in libraries:
        _assert_library_tenant_scope(library, current_user.tenant_id)

    return [LibraryListItem.model_validate(library) for library in libraries]


@router.patch("/{id}", response_model=LibraryListItem)
@router.put("/{id}", response_model=LibraryListItem, include_in_schema=False)
async def update_library(
    id: int,
    payload: LibraryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    _auth: AuthContext = Depends(require_admin),
) -> LibraryListItem:
    library = await _get_tenant_library_or_404(db, id, current_user.tenant_id)

    if payload.name is not None:
        library.name = payload.name.strip()
    if payload.code is not None:
        library.code = LibraryService.normalize_code(payload.code)
    if payload.timezone is not None:
        library.timezone = payload.timezone.strip() or library.timezone
    if payload.is_active is not None:
        library.is_active = payload.is_active

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Library code already exists in tenant") from exc

    await db.refresh(library)
    return LibraryListItem.model_validate(library)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    _auth: AuthContext = Depends(require_admin),
) -> None:
    library = await _get_tenant_library_or_404(db, id, current_user.tenant_id)
    await db.delete(library)
    await db.commit()


@router.get("/{id}/policy", response_model=LibraryPolicyRead)
async def get_library_policy(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> LibraryPolicyRead:
    library = await _get_tenant_library_or_404(db, id, current_user.tenant_id)
    policy = (
        await db.execute(
            select(LibraryPolicy).where(LibraryPolicy.library_id == library.id)
        )
    ).scalar_one_or_none()

    if policy is None:
        policy = LibraryPolicy(library_id=library.id)
        db.add(policy)
        await db.commit()
        await db.refresh(policy)

    return LibraryPolicyRead.model_validate(policy)


@router.put("/{id}/policy", response_model=LibraryPolicyRead)
async def upsert_library_policy(
    id: int,
    payload: LibraryPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    _auth: AuthContext = Depends(require_admin),
) -> LibraryPolicyRead:
    library = await _get_tenant_library_or_404(db, id, current_user.tenant_id)

    policy = (
        await db.execute(
            select(LibraryPolicy).where(LibraryPolicy.library_id == library.id)
        )
    ).scalar_one_or_none()

    if policy is None:
        policy = LibraryPolicy(library_id=library.id)
        db.add(policy)

    policy.max_loans = payload.max_loans
    policy.loan_days = payload.loan_days
    policy.fine_per_day = payload.fine_per_day
    policy.renewal_limit = payload.renewal_limit

    await db.commit()
    await db.refresh(policy)

    return LibraryPolicyRead.model_validate(policy)
