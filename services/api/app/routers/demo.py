from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.database import get_db
from app.deps import require_rank
from app.ingest import apply_detections, auto_analyze_significant, persist_events
from app.models import Alert, DemoWorkspace, Device, Membership, new_id

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

DEMO_LABEL = "LABELED DEMO — not live telemetry"
DEMO_HOSTNAME = "DEMO-WORKSTATION"


def demo_payload(extra: dict | None = None) -> dict:
    data = {"demo": True, "label": DEMO_LABEL}
    if extra:
        data.update(extra)
    return data


async def demo_workspace(db: AsyncSession, organization_id: str) -> DemoWorkspace | None:
    return await db.get(DemoWorkspace, organization_id)


@router.get("")
async def demo_status(db: AsyncSession = Depends(get_db), membership: Membership = Depends(require_rank("VIEWER"))) -> dict:
    row = await demo_workspace(db, membership.organization_id)
    return {
        "loaded": row is not None,
        "label": row.label if row else DEMO_LABEL,
        "loaded_at": row.loaded_at.isoformat() if row and row.loaded_at else None,
    }


@router.post("/load")
async def load_demo(
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("ADMIN")),
) -> dict:
    existing = await demo_workspace(db, membership.organization_id)
    if existing:
        return {"ok": True, "already_loaded": True, "label": existing.label, "notice": existing.label}

    live = (
        await db.execute(
            select(Device).where(
                Device.organization_id == membership.organization_id,
                Device.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    if any(not (item.health_json or {}).get("demo") for item in live):
        raise HTTPException(
            status_code=409,
            detail="Refusing to mix labeled demo data with live tenant telemetry. Use an empty organization, or a demo-only workspace.",
        )

    now = datetime.now(UTC)
    device = Device(
        id=new_id(),
        organization_id=membership.organization_id,
        name="[DEMO] Screenshot workstation",
        hostname=DEMO_HOSTNAME,
        os_name="Windows",
        os_version="demo",
        agent_version="0.1.0-demo",
        status="online",
        last_seen_at=now,
        health_json=demo_payload({"can_read_security_log": True}),
        posture_json={"defender_status": "off", "firewall_status": "on", "demo": True, "label": DEMO_LABEL},
    )
    db.add(device)
    await db.flush()

    events = [
        *[{"category": "authentication", "event_type": "auth_failure", "payload": demo_payload({"account": "demo.user"})} for _ in range(5)],
        {"category": "authentication", "event_type": "auth_success", "payload": demo_payload({"account": "demo.user"})},
        {"category": "windows_security", "event_type": "privileged_account_created", "payload": demo_payload({"account": "demo.admin"})},
        {
            "category": "process",
            "event_type": "process_start",
            "payload": demo_payload({"cmdline": "powershell.exe -enc ZGVtbw==", "path": "C:\\Windows\\Temp\\demo.ps1"}),
        },
        {
            "category": "security_control",
            "event_type": "posture",
            "payload": demo_payload({"defender_status": "off", "firewall_status": "on"}),
        },
    ]
    rows = await persist_events(db, organization_id=membership.organization_id, device_id=device.id, items=events)
    await apply_detections(db, organization_id=membership.organization_id, device_id=device.id, events=rows)

    critical = Alert(
        id=new_id(),
        organization_id=membership.organization_id,
        device_id=device.id,
        title="[DEMO] Critical: simulated credential stuffing after a privilege change",
        severity="critical",
        confidence=0.99,
        risk_score=95,
        detection_source="demo",
        rule_id="demo_critical_screenshot",
        evidence_json=demo_payload({"note": "Inserted for screenshots. Not live telemetry."}),
        recommended_next_step="This is labeled demo data. Do not treat it as a real incident. Enroll a real agent in a separate organization for live detection.",
    )
    db.add(critical)
    await db.flush()
    await auto_analyze_significant(db, membership.organization_id, [critical], limit=1)
    db.add(critical)
    await db.flush()
    await auto_analyze_significant(db, membership.organization_id, [critical], limit=1)
    db.add(
        DemoWorkspace(
            organization_id=membership.organization_id,
            label=DEMO_LABEL,
            loaded_at=now,
        )
    )
    await write_audit(
        db,
        action="demo.load",
        actor_type="user",
        actor_id=membership.user_id,
        organization_id=membership.organization_id,
        resource_type="organization",
        resource_id=membership.organization_id,
    )
    await db.commit()
    return {
        "ok": True,
        "already_loaded": False,
        "label": DEMO_LABEL,
        "notice": "Labeled demo data loaded. It is not live telemetry and must not be mixed with a real agent.",
        "device_id": device.id,
    }
