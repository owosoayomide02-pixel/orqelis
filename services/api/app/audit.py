from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, new_id


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_type: str = "user",
    actor_id: str | None = None,
    organization_id: str | None = None,
    resource_type: str = "",
    resource_id: str = "",
    details: dict | None = None,
    ip_address: str = "",
) -> AuditLog:
    row = AuditLog(
        id=new_id(),
        organization_id=organization_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=details or {},
        ip_address=ip_address,
        created_at=datetime.now(UTC),
    )
    db.add(row)
    return row
