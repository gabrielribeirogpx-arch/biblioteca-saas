from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import Library


class LibraryService:
    @staticmethod
    def normalize_code(code: str) -> str:
        return code.strip().lower()

    @staticmethod
    def normalize_name(name: str) -> str:
        return name.strip()

    @staticmethod
    def generate_code_from_name(name: str) -> str:
        generated_code = "-".join(name.strip().lower().split())
        return generated_code[:64]

    @staticmethod
    async def create_library(
        db: AsyncSession,
        *,
        tenant_id: int,
        organization_id: int,
        name: str,
        code: str | None = None,
        timezone: str = "America/Sao_Paulo",
        is_active: bool = True,
    ) -> Library:
        normalized_name = LibraryService.normalize_name(name)
        normalized_code = LibraryService.normalize_code(code) if code else LibraryService.generate_code_from_name(normalized_name)
        normalized_timezone = timezone.strip() if timezone and timezone.strip() else "America/Sao_Paulo"

        if not normalized_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")
        if not normalized_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code is required")

        duplicate = (
            await db.execute(
                select(Library).where(
                    Library.tenant_id == tenant_id,
                    Library.code == normalized_code,
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Library code already exists in tenant")

        library = Library(
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=normalized_name,
            code=normalized_code,
            timezone=normalized_timezone,
            is_active=is_active,
        )
        db.add(library)

        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Library code already exists in tenant") from exc

        await db.refresh(library)
        return library

    @staticmethod
    async def list_libraries(db: AsyncSession, *, tenant_id: int) -> list[Library]:
        result = await db.execute(
            select(Library)
            .where(Library.tenant_id == tenant_id)
            .order_by(Library.name.asc())
        )
        return list(result.scalars().all())
