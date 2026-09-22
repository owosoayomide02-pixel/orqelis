from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_membership
from app.models import Alert, DemoWorkspace, Device, Incident, Membership, Organization, Vulnerability
from app.scoring import compute_score

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


@router.get("/current")
async def current_org(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    org = await db.get(Organization, membership.organization_id)
    devices = (await db.execute(select(func.count()).select_from(Device).where(Device.organization_id == membership.organization_id))).scalar() or 0
    alerts = (await db.execute(select(func.count()).select_from(Alert).where(Alert.organization_id == membership.organization_id))).scalar() or 0
    incidents = (await db.execute(select(func.count()).select_from(Incident).where(Incident.organization_id == membership.organization_id))).scalar() or 0
    vulns = (await db.execute(select(func.count()).select_from(Vulnerability).where(Vulnerability.organization_id == membership.organization_id))).scalar() or 0
    demo = await db.get(DemoWorkspace, membership.organization_id)
    return {
        "id": org.id if org else membership.organization_id,
        "name": org.name if org else "",
        "role": membership.role,
        "demo": demo is not None,
        "demo_label": demo.label if demo else None,
        "counts": {"devices": devices, "alerts": alerts, "incidents": incidents, "vulnerabilities": vulns},
    }


@router.get("/current/score")
async def current_score(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> dict:
    org_id = membership.organization_id
    device_rows = (await db.execute(select(Device).where(Device.organization_id == org_id))).scalars().all()
    alert_rows = (await db.execute(select(Alert).where(Alert.organization_id == org_id))).scalars().all()
    incident_rows = (await db.execute(select(Incident).where(Incident.organization_id == org_id))).scalars().all()
    vuln_rows = (await db.execute(select(Vulnerability).where(Vulnerability.organization_id == org_id))).scalars().all()
    return compute_score(devices=list(device_rows), alerts=list(alert_rows), incidents=list(incident_rows), vulnerabilities=list(vuln_rows))

