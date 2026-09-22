from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.database import get_db
from app.deps import get_membership, require_rank
from app.models import ActionRecord, AgentCommand, ApprovalRequest, Membership, new_id

router = APIRouter(prefix="/api/v1", tags=["approvals"])

ALLOWED_KINDS = {"refresh_policy", "restart_agent"}
KIND_RISK = {"refresh_policy": "low", "restart_agent": "low"}


class RecommendPayload(BaseModel):
    device_id: str
    kind: str
    title: str = ""
    reason: str = ""


class DecisionPayload(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


@router.get("/approvals")
async def list_approvals(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> list[dict]:
    rows = (
        await db.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.organization_id == membership.organization_id)
            .order_by(ApprovalRequest.created_at.desc())
        )
    ).scalars().all()
    return [_approval_out(row) for row in rows]


@router.get("/actions")
async def list_actions(db: AsyncSession = Depends(get_db), membership: Membership = Depends(get_membership)) -> list[dict]:
    rows = (
        await db.execute(select(ActionRecord).where(ActionRecord.organization_id == membership.organization_id).order_by(ActionRecord.created_at.desc()))
    ).scalars().all()
    return [
        {
            "id": row.id,
            "device_id": row.device_id,
            "kind": row.kind,
            "title": row.title,
            "risk_class": row.risk_class,
            "status": row.status,
            "details": row.details_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("/actions/recommend")
async def recommend_action(
    payload: RecommendPayload,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
) -> dict:
    if payload.kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="Unsupported action kind")
    risk = KIND_RISK[payload.kind]
    action = ActionRecord(
        id=new_id(),
        organization_id=membership.organization_id,
        device_id=payload.device_id,
        kind=payload.kind,
        title=payload.title or payload.kind.replace("_", " ").title(),
        details_json={"reason": payload.reason},
        risk_class=risk,
        status="pending_approval" if risk != "low" else "recommended",
    )
    db.add(action)
    await db.flush()
    approval = ApprovalRequest(
        id=new_id(),
        organization_id=membership.organization_id,
        requested_by_user_id=membership.user_id,
        action_id=action.id,
        title=action.title,
        reason=payload.reason,
        risk_class=risk,
        status="pending",
    )
    db.add(approval)
    await write_audit(
        db,
        action="action.recommend",
        actor_type="user",
        actor_id=membership.user_id,
        organization_id=membership.organization_id,
        resource_type="action",
        resource_id=action.id,
        details={"kind": payload.kind, "risk_class": risk},
    )
    await db.commit()
    return {"action_id": action.id, "approval_id": approval.id, "risk_class": risk}


@router.post("/approvals/{approval_id}/decide")
async def decide(
    approval_id: str,
    payload: DecisionPayload,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("ADMIN")),
) -> dict:
    row = await db.get(ApprovalRequest, approval_id)
    if row is None or row.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Approval not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided")
    row.status = "approved" if payload.decision == "approve" else "rejected"
    row.decided_by_user_id = membership.user_id
    row.decided_at = datetime.now(UTC)
    action = await db.get(ActionRecord, row.action_id) if row.action_id else None
    if action:
        action.status = "approved" if payload.decision == "approve" else "rejected"
        if payload.decision == "approve" and action.kind in ALLOWED_KINDS and action.device_id:
            db.add(
                AgentCommand(
                    id=new_id(),
                    organization_id=membership.organization_id,
                    device_id=action.device_id,
                    kind=action.kind,
                    payload_json={},
                    status="pending",
                )
            )
            action.status = "executed"
    await write_audit(
        db,
        action="approval.decide",
        actor_type="user",
        actor_id=membership.user_id,
        organization_id=membership.organization_id,
        resource_type="approval",
        resource_id=row.id,
        details={"decision": payload.decision},
    )
    await db.commit()
    return _approval_out(row)


def _approval_out(row: ApprovalRequest) -> dict:
    return {
        "id": row.id,
        "action_id": row.action_id,
        "title": row.title,
        "reason": row.reason,
        "risk_class": row.risk_class,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }
