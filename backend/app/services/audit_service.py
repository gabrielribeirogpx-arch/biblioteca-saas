from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditActorType, AuditCategory, AuditLog


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        library_id: int,
        category: AuditCategory,
        actor_type: AuditActorType,
        actor_id: int | None,
        action: str,
        entity_type: str,
        entity_id: str,
        summary: str,
        tenant_id: int | None = None,
        organization_id: int | None = None,
        payload: dict | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        event = AuditLog(
            tenant_id=tenant_id,
            library_id=library_id,
            organization_id=organization_id,
            category=category,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            payload=payload or {},
            request_id=request_id,
            ip_address=ip_address,
        )
        db.add(event)
        await db.commit()
