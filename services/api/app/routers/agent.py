from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.database import get_db
from app.deps import get_current_device
from app.ingest import apply_detections, persist_events
from app.models import AgentCommand, DemoWorkspace, Device, DeviceEnrollment, Policy, new_id
from orqelis_security.tokens import hash_secret, new_secret
from orqelis_shared.constants import ALLOWED_EVENT_CATEGORIES

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class EnrollPayload(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    hostname: str = Field(default="", max_length=160)
    os_name: str = Field(default="Windows", max_length=80)
    os_version: str = Field(default="", max_length=80)
    agent_version: str = Field(default="0.1.0", max_length=32)


class EventItem(BaseModel):
    category: str
    event_type: str = "snapshot"
    occurred_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventBatch(BaseModel):
    events: list[EventItem] = Field(default_factory=list, max_length=200)


class HeartbeatPayload(BaseModel):
    health: dict[str, Any] = Field(default_factory=dict)
    posture: dict[str, Any] = Field(default_factory=dict)


class CommandAck(BaseModel):
    command_ids: list[str] = Field(default_factory=list)


@router.post("/enroll")
async def enroll(payload: EnrollPayload, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    code = payload.code.strip().replace(" ", "")
    enrollment = (
        await db.execute(select(DeviceEnrollment).where(DeviceEnrollment.code_hash == hash_secret(code)))
    ).scalar_one_or_none()
    if enrollment is None or enrollment.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid enrollment code")
    if await db.get(DemoWorkspace, enrollment.organization_id) is not None:
        raise HTTPException(
            status_code=409,
            detail="This organization contains labeled demo data. Enroll a live agent in a separate organization.",
        )
    expires = enrollment.expires_at.replace(tzinfo=UTC) if enrollment.expires_at.tzinfo is None else enrollment.expires_at
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Enrollment code expired")
    token = new_secret()
    device = Device(
        id=new_id(),
        organization_id=enrollment.organization_id,
        name=payload.hostname or "Windows device",
        hostname=payload.hostname,
        os_name=payload.os_name,
        os_version=payload.os_version,
        agent_version=payload.agent_version,
        status="online",
        token_hash=hash_secret(token),
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    await db.flush()
    enrollment.device_id = device.id
    enrollment.used_at = datetime.now(UTC)
    await write_audit(
        db,
        action="device.enroll",
        actor_type="agent",
        actor_id=device.id,
        organization_id=device.organization_id,
        resource_type="device",
        resource_id=device.id,
        ip_address=request.client.host if request.client else "",
    )
    await db.commit()
    return {
        "device_id": device.id,
        "device_token": token,
        "organization_id": device.organization_id,
        "notice": (
            "Orqelis Endpoint Security collects security telemetry necessary to provide endpoint protection. "
            "By enrolling this agent you confirm you are authorized to operate it on this device."
        ),
    }


@router.post("/heartbeat")
async def heartbeat(
    payload: HeartbeatPayload,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> dict[str, Any]:
    device.last_seen_at = datetime.now(UTC)
    device.status = "online"
    device.health_json = payload.health
    device.posture_json = payload.posture
    commands = (
        await db.execute(
            select(AgentCommand).where(
                AgentCommand.device_id == device.id,
                AgentCommand.status == "pending",
            )
        )
    ).scalars().all()
    policy = (
        await db.execute(select(Policy).where(Policy.organization_id == device.organization_id))
    ).scalars().first()
    await db.commit()
    return {
        "ok": True,
        "policy": _policy_out(policy),
        "commands": [
            {"id": row.id, "kind": row.kind, "payload": row.payload_json}
            for row in commands
            if row.kind in {"refresh_policy", "restart_agent"}
        ],
    }


@router.post("/events")
async def ingest_events(
    payload: EventBatch,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> dict[str, Any]:
    allowed = []
    for item in payload.events:
        if item.category not in ALLOWED_EVENT_CATEGORIES:
            continue
        allowed.append(item.model_dump())
    if not allowed:
        return {"accepted": 0, "alerts": 0, "incidents": 0}
    rows = await persist_events(db, organization_id=device.organization_id, device_id=device.id, items=allowed)
    result = await apply_detections(db, organization_id=device.organization_id, device_id=device.id, events=rows)
    device.last_seen_at = datetime.now(UTC)
    device.status = "online"
    await db.commit()
    return {
        "accepted": len(rows),
        "alerts": len(result["alerts"]),
        "incidents": len(result["incidents"]),
        "vulnerabilities": len(result["vulnerabilities"]),
    }


@router.post("/commands/ack")
async def ack_commands(
    payload: CommandAck,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> dict:
    now = datetime.now(UTC)
    for command_id in payload.command_ids:
        row = await db.get(AgentCommand, command_id)
        if row and row.device_id == device.id:
            row.status = "acked"
            row.acked_at = now
    await db.commit()
    return {"ok": True}


@router.get("/policy")
async def agent_policy(db: AsyncSession = Depends(get_db), device: Device = Depends(get_current_device)) -> dict:
    policy = (await db.execute(select(Policy).where(Policy.organization_id == device.organization_id))).scalars().first()
    return _policy_out(policy)


def _policy_out(policy: Policy | None) -> dict[str, Any]:
    if policy is None:
        return {
            "collect_process_metadata": True,
            "collect_security_events": True,
            "collect_network_metadata": True,
            "heartbeat_seconds": 30,
            "batch_max_events": 100,
        }
    return {
        "id": policy.id,
        "collect_process_metadata": policy.collect_process_metadata,
        "collect_security_events": policy.collect_security_events,
        "collect_network_metadata": policy.collect_network_metadata,
        "heartbeat_seconds": policy.heartbeat_seconds,
        "batch_max_events": policy.batch_max_events,
    }
