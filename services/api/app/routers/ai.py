from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_membership, require_rank
from app.ingest import store_analysis
from app.models import AIAnalysis, Alert, Incident, Membership, Vulnerability
from orqelis_ai.gateway import AIGateway
from orqelis_shared.constants import AI_ROLES

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


def _gateway() -> AIGateway:
    return AIGateway(
        provider=settings.resolved_ai_provider,
        api_key=settings.resolved_ai_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
    )


class AnalyzePayload(BaseModel):
    role: str = Field(default="analyst")
    subject_type: str
    subject_id: str


@router.post("/analyze")
async def analyze(
    payload: AnalyzePayload,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
) -> dict:
    role = payload.role.lower()
    if role not in AI_ROLES:
        raise HTTPException(status_code=400, detail="Unknown AI role")
    record = await _load_subject(db, membership.organization_id, payload.subject_type, payload.subject_id)
    analysis = await store_analysis(
        db,
        _gateway(),
        organization_id=membership.organization_id,
        role=role,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        payload=record,
    )
    await db.commit()
    return {
        "id": analysis.id,
        "role": analysis.role,
        "provider": analysis.provider,
        "model": analysis.model,
        "output": analysis.output_json,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }


@router.get("/analyses")
async def list_analyses(
    subject_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> list[dict]:
    query = select(AIAnalysis).where(AIAnalysis.organization_id == membership.organization_id)
    if subject_id:
        query = query.where(AIAnalysis.subject_id == subject_id)
    rows = (await db.execute(query.order_by(AIAnalysis.created_at.desc()).limit(50))).scalars().all()
    return [
        {
            "id": row.id,
            "role": row.role,
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "provider": row.provider,
            "output": row.output_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


async def _load_subject(db: AsyncSession, organization_id: str, subject_type: str, subject_id: str) -> dict:
    if subject_type == "alert":
        row = await db.get(Alert, subject_id)
        if row is None or row.organization_id != organization_id:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {
            "title": row.title,
            "severity": row.severity,
            "risk_score": row.risk_score,
            "evidence": row.evidence_json,
            "recommended_next_step": row.recommended_next_step,
        }
    if subject_type == "incident":
        row = await db.get(Incident, subject_id)
        if row is None or row.organization_id != organization_id:
            raise HTTPException(status_code=404, detail="Incident not found")
        return {
            "title": row.title,
            "summary": row.summary,
            "severity": row.severity,
            "risk_score": row.risk_score,
            "status": row.status,
        }
    if subject_type == "vulnerability":
        row = await db.get(Vulnerability, subject_id)
        if row is None or row.organization_id != organization_id:
            raise HTTPException(status_code=404, detail="Vulnerability not found")
        return {
            "title": row.title,
            "description": row.description,
            "severity": row.severity,
            "evidence": row.evidence_json,
        }
    raise HTTPException(status_code=400, detail="Unsupported subject type")
