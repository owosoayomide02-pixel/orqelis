from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_downloads import binary_path, catalog
from app.audit import write_audit
from app.config import settings
from app.database import get_db
from app.deps import get_membership, require_rank
from app.models import AgentVersion, Alert, Device, DeviceEnrollment, Membership, SecurityEvent, new_id
from app.scoring import is_online, posture_checklist
from secrets import randbelow

from orqelis_security.tokens import hash_secret

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


class EnrollmentCreate(BaseModel):
    ttl_minutes: int = Field(default=30, ge=5, le=1440)


@router.get("")
async def list_devices(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> list[dict]:
    rows = (
        await db.execute(select(Device).where(Device.organization_id == membership.organization_id, Device.revoked_at.is_(None)))
    ).scalars().all()
    now = datetime.now(UTC)
    out = []
    for row in rows:
        last = row.last_seen_at
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        online = bool(last and now - last < timedelta(minutes=2))
        if row.status != "revoked":
            row.status = "online" if online else "offline"
        out.append(_device_out(row))
    await db.commit()
    return out


@router.get("/agent-downloads")
async def agent_downloads(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    versions = (await db.execute(select(AgentVersion).order_by(AgentVersion.platform))).scalars().all()
    return {
        "notice": "Signed MSI/pkg/deb installers are not in V1. Use the Python agent or a local PyInstaller build.",
        "platforms": catalog(list(versions), settings.resolved_public_api_url),
    }


@router.get("/agent-downloads/{platform}")
async def download_agent(
    platform: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> FileResponse:
    path = binary_path(platform)
    if path is None:
        raise HTTPException(status_code=404, detail="Packaged agent is not built on this machine. Use the Python enroll commands, or run the package script for this OS.")
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")


@router.get("/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    row = await db.get(Device, device_id)
    if row is None or row.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Device not found")
    high = (
        await db.execute(
            select(Alert).where(
                Alert.organization_id == membership.organization_id,
                Alert.device_id == row.id,
                Alert.status == "open",
                Alert.severity.in_(("high", "critical")),
            )
        )
    ).scalars().all()
    events = (
        await db.execute(
            select(SecurityEvent)
            .where(SecurityEvent.organization_id == membership.organization_id, SecurityEvent.device_id == row.id)
            .order_by(SecurityEvent.occurred_at.desc())
            .limit(25)
        )
    ).scalars().all()
    data = _device_out(row)
    data["online"] = is_online(row)
    data["posture_checklist"] = posture_checklist(row, high_open_alerts=len(high))
    data["open_high_alerts"] = [_alert_brief(item) for item in high]
    data["recent_events"] = [
        {
            "id": event.id,
            "category": event.category,
            "event_type": event.event_type,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        }
        for event in events
    ]
    return data


@router.post("/enrollments")
async def create_enrollment(
    payload: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("ADMIN")),
) -> dict[str, Any]:
    numeric = f"{randbelow(1_000_000):06d}"
    row = DeviceEnrollment(
        id=new_id(),
        organization_id=membership.organization_id,
        code_hash=hash_secret(numeric),
        created_by_user_id=membership.user_id,
        expires_at=datetime.now(UTC) + timedelta(minutes=payload.ttl_minutes),
    )
    db.add(row)
    await write_audit(
        db,
        action="device.enrollment.create",
        actor_type="user",
        actor_id=membership.user_id,
        organization_id=membership.organization_id,
        resource_type="enrollment",
        resource_id=row.id,
    )
    await db.commit()
    return {
        "enrollment_id": row.id,
        "code": numeric,
        "expires_at": row.expires_at.isoformat(),
        "notice": "Install the Orqelis agent only on Windows, macOS, or Linux devices you own or are authorized to manage.",
    }


@router.post("/{device_id}/revoke")
async def revoke_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("ADMIN")),
) -> dict:
    row = await db.get(Device, device_id)
    if row is None or row.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Device not found")
    row.revoked_at = datetime.now(UTC)
    row.status = "revoked"
    row.token_hash = None
    await write_audit(
        db,
        action="device.revoke",
        actor_type="user",
        actor_id=membership.user_id,
        organization_id=membership.organization_id,
        resource_type="device",
        resource_id=row.id,
    )
    await db.commit()
    return {"ok": True}


def _alert_brief(row: Alert) -> dict[str, Any]:
    return {"id": row.id, "title": row.title, "severity": row.severity}


def _device_out(row: Device) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "hostname": row.hostname,
        "os_name": row.os_name,
        "os_version": row.os_version,
        "agent_version": row.agent_version,
        "status": row.status,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "health": row.health_json,
        "posture": row.posture_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
