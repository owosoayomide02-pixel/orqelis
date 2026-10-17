"""Web asset management, DNS verification, Hunter scans, and AI role actions."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.config import settings
from app.database import SessionLocal, get_db
from app.deps import get_current_user, get_membership, require_rank
from app.domain_validation import domain_resolves_to_private, validate_domain
from app.ingest import persist_web_findings, store_analysis
from app.models import (
    Alert,
    Membership,
    Report,
    ScanJob,
    SecurityEvent,
    User,
    WebAssetEvidence,
    WebAsset,
    new_id,
)
from app.quotas import monthly_scan_count, org_limits, usage, web_asset_count
from app.scanner import execute_scan, normalize_raw
from app.scoring import compute_web_risk
from orqelis_ai.gateway import AIGateway

log = logging.getLogger("orqelis.web_assets")
router = APIRouter(prefix="/api/v1", tags=["web-assets"])
MAX_EVIDENCE_BYTES = 800_000
IMAGE_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/webp": (b"RIFF",),
}


def _gateway(role: str = "analyst") -> AIGateway:
    return AIGateway(
        provider=settings.resolved_ai_provider,
        api_key=settings.resolved_ai_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        model_light=settings.ai_model_light,
        model_heavy=settings.ai_model_heavy,
        fallback_provider=settings.resolved_ai_fallback_provider,
        fallback_api_key=settings.resolved_ai_fallback_key,
    )


def _verification_instructions(asset: WebAsset) -> dict[str, str]:
    return {
        "record_type": "TXT",
        "record_name": f"_orqelis-verify.{asset.domain}",
        "record_value": f"orqelis-verify={asset.verification_token}",
    }


def _asset_out(
    asset: WebAsset, *, include_instructions: bool = False, summary: dict[str, Any] | None = None
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": asset.id,
        "domain": asset.domain,
        "verification_status": asset.verification_status,
        "verification_method": asset.verification_method,
        "verified_at": asset.verified_at.isoformat() if asset.verified_at else None,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "archived": asset.archived,
    }
    if summary is not None:
        data.update(summary)
    if include_instructions or asset.verification_status != "verified":
        data["verification_instructions"] = _verification_instructions(asset)
    return data


async def _web_alerts_by_asset(db: AsyncSession, organization_id: str) -> dict[str, list[Alert]]:
    rows = (
        await db.execute(
            select(Alert)
            .where(
                Alert.organization_id == organization_id,
                Alert.device_id.is_(None),
                Alert.detection_source == "hunter",
            )
            .order_by(Alert.created_at.desc())
        )
    ).scalars().all()
    grouped: dict[str, list[Alert]] = {}
    for row in rows:
        asset_id = (row.evidence_json or {}).get("web_asset_id")
        if asset_id:
            grouped.setdefault(asset_id, []).append(row)
    return grouped


async def _asset_summaries(db: AsyncSession, organization_id: str, assets: list[WebAsset]) -> dict[str, dict[str, Any]]:
    """Risk score, open findings, and last scan for each asset, computed in two queries."""
    if not assets:
        return {}
    alerts = await _web_alerts_by_asset(db, organization_id)
    scans = (
        await db.execute(
            select(ScanJob)
            .where(ScanJob.organization_id == organization_id, ScanJob.web_asset_id.in_([a.id for a in assets]))
            .order_by(ScanJob.created_at.desc())
        )
    ).scalars().all()
    last_scan: dict[str, ScanJob] = {}
    completed: set[str] = set()
    for job in scans:
        last_scan.setdefault(job.web_asset_id, job)
        if job.status == "completed":
            completed.add(job.web_asset_id)
    out: dict[str, dict[str, Any]] = {}
    for asset in assets:
        risk = compute_web_risk(alerts=alerts.get(asset.id, []), scanned=asset.id in completed)
        job = last_scan.get(asset.id)
        by_sev = risk.get("by_severity") or {}
        if asset.id not in completed:
            health = "unscanned"
        elif by_sev.get("critical", 0) > 0 or by_sev.get("high", 0) > 0:
            health = "critical"
        elif by_sev.get("medium", 0) > 0:
            health = "degraded"
        else:
            health = "healthy"
        out[asset.id] = {
            **risk,
            "health_status": health,
            "has_completed_scan": asset.id in completed,
            "last_scan": (
                {
                    "id": job.id,
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                }
                if job
                else None
            ),
        }
    return out


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


class CreateWebAssetPayload(BaseModel):
    domain: str = Field(min_length=3, max_length=253)


class ScanPayload(BaseModel):
    role: str = Field(default="hunter")


async def _get_asset(
    db: AsyncSession, asset_id: str, organization_id: str, *, allow_archived: bool = False
) -> WebAsset:
    asset = await db.get(WebAsset, asset_id)
    if asset is None or asset.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Web asset not found")
    if asset.archived and not allow_archived:
        raise HTTPException(status_code=404, detail="Web asset not found")
    return asset


@router.get("/web-assets")
async def list_web_assets(
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> list[dict]:
    rows = (
        await db.execute(
            select(WebAsset)
            .where(WebAsset.organization_id == membership.organization_id, WebAsset.archived.is_(False))
            .order_by(WebAsset.created_at.desc())
        )
    ).scalars().all()
    summaries = await _asset_summaries(db, membership.organization_id, list(rows))
    return [_asset_out(row, summary=summaries.get(row.id)) for row in rows]


@router.get("/web-assets/usage")
async def web_asset_usage(
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> dict:
    return await usage(db, membership.organization_id)


@router.get("/web-assets/risk-summary")
async def web_risk_summary(
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> dict:
    """Org-wide web exposure: the worst scanned asset sets the headline number."""
    rows = (
        await db.execute(
            select(WebAsset).where(
                WebAsset.organization_id == membership.organization_id, WebAsset.archived.is_(False)
            )
        )
    ).scalars().all()
    summaries = await _asset_summaries(db, membership.organization_id, list(rows))
    scored = [(row, summaries[row.id]) for row in rows if summaries[row.id]["risk_score"] is not None]
    worst = max(scored, key=lambda item: item[1]["risk_score"], default=None)
    by_severity = {sev: 0 for sev in ("critical", "high", "medium", "low")}
    for summary in summaries.values():
        for sev, count in summary["by_severity"].items():
            by_severity[sev] += count
    return {
        "risk_score": worst[1]["risk_score"] if worst else None,
        "worst_asset": {"id": worst[0].id, "domain": worst[0].domain} if worst else None,
        "assets_total": len(rows),
        "assets_verified": sum(1 for r in rows if r.verification_status == "verified"),
        "assets_scanned": len(scored),
        "open_findings": sum(s["open_findings"] for s in summaries.values()),
        "by_severity": by_severity,
    }


@router.post("/web-assets", status_code=201)
async def create_web_asset(
    payload: CreateWebAssetPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        domain = validate_domain(payload.domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if domain_resolves_to_private(domain):
        # In development allow unverified/unresolvable domains so local demos work;
        # still reject clearly private resolutions.
        try:
            import socket as _socket

            _socket.getaddrinfo(domain, None)
            raise HTTPException(status_code=400, detail="Domain resolves to a private address and cannot be scanned")
        except OSError:
            if not settings.is_development:
                raise HTTPException(status_code=400, detail="Domain could not be resolved") from None
        except HTTPException:
            raise

    other = (
        await db.execute(
            select(WebAsset).where(
                WebAsset.domain == domain,
                WebAsset.verification_status == "verified",
                WebAsset.organization_id != membership.organization_id,
                WebAsset.archived.is_(False),
            )
        )
    ).scalars().first()
    if other is not None:
        raise HTTPException(status_code=403, detail="Domain is already verified under another organization")

    existing = (
        await db.execute(
            select(WebAsset).where(
                WebAsset.organization_id == membership.organization_id,
                WebAsset.domain == domain,
                WebAsset.archived.is_(False),
            )
        )
    ).scalars().first()
    if existing is not None:
        # Idempotent create — return existing (spec: 409 own-org returns existing)
        return _asset_out(existing, include_instructions=True)

    limits = await org_limits(db, membership.organization_id)
    asset_limit = limits["web_assets"]
    if asset_limit is not None and await web_asset_count(db, membership.organization_id) >= asset_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Web asset limit reached ({asset_limit} on {limits['plan_name']}). Upgrade your plan to add more domains.",
        )

    token = secrets.token_hex(16)
    asset = WebAsset(
        id=new_id(),
        organization_id=membership.organization_id,
        domain=domain,
        verification_status="unverified",
        verification_method="dns_txt",
        verification_token=token,
        created_by_user_id=user.id,
    )
    db.add(asset)
    await write_audit(
        db,
        action="web_asset.create",
        actor_id=user.id,
        organization_id=membership.organization_id,
        resource_type="web_asset",
        resource_id=asset.id,
        details={"domain": domain},
        ip_address=_client_ip(request),
    )
    await db.commit()
    await db.refresh(asset)
    return _asset_out(asset, include_instructions=True)


@router.get("/web-assets/{asset_id}")
async def get_web_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> dict:
    asset = await _get_asset(db, asset_id, membership.organization_id)
    summaries = await _asset_summaries(db, membership.organization_id, [asset])
    return _asset_out(asset, include_instructions=True, summary=summaries[asset.id])


async def _lookup_txt(name: str) -> list[str]:
    try:
        import dns.resolver  # type: ignore

        answers = dns.resolver.resolve(name, "TXT")
        values: list[str] = []
        for rdata in answers:
            for txt in getattr(rdata, "strings", []) or []:
                if isinstance(txt, bytes):
                    values.append(txt.decode("utf-8", errors="replace"))
                else:
                    values.append(str(txt))
            text = getattr(rdata, "to_text", lambda: "")()
            if text:
                values.append(text.strip('"'))
        return values
    except Exception:
        # Fallback: dnspython may be absent — use socket getaddrinfo is wrong for TXT.
        try:
            import subprocess

            proc = await asyncio.create_subprocess_exec(
                "nslookup",
                "-type=TXT",
                name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            text = stdout.decode("utf-8", errors="replace")
            return [line.strip() for line in text.splitlines() if "orqelis-verify=" in line]
        except Exception:
            return []


@router.post("/web-assets/{asset_id}/verify")
async def verify_web_asset(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
    user: User = Depends(get_current_user),
) -> dict:
    asset = await _get_asset(db, asset_id, membership.organization_id)
    now = datetime.now(UTC)
    last_attempt = asset.last_verify_attempt_at
    if last_attempt:
        if last_attempt.tzinfo is None:
            last_attempt = last_attempt.replace(tzinfo=UTC)
        elapsed = (now - last_attempt).total_seconds()
        if elapsed < settings.dns_verify_rate_limit_seconds:
            raise HTTPException(
                status_code=429,
                detail=f"Wait {int(settings.dns_verify_rate_limit_seconds - elapsed)}s before retrying verification",
            )
    asset.last_verify_attempt_at = now

    expected = f"orqelis-verify={asset.verification_token}"
    found = False
    # Stub / test verify only in development — never in production deploys
    if settings.is_development and (
        settings.dns_verify_stub or request.headers.get("X-Orqelis-Test-Verify") == "1"
    ):
        found = True
    else:
        records = await _lookup_txt(f"_orqelis-verify.{asset.domain}")
        found = any(expected in rec.replace('"', "") for rec in records)

    if found:
        asset.verification_status = "verified"
        asset.verified_at = now
        await write_audit(
            db,
            action="web_asset.verify",
            actor_id=user.id,
            organization_id=membership.organization_id,
            resource_type="web_asset",
            resource_id=asset.id,
            details={"domain": asset.domain},
            ip_address=_client_ip(request),
        )
        await db.commit()
        return {
            "id": asset.id,
            "verification_status": "verified",
            "verified_at": asset.verified_at.isoformat(),
        }

    await db.commit()
    return {
        "id": asset.id,
        "verification_status": "unverified",
        "message": "TXT record not found yet. DNS changes can take up to 24 hours to propagate.",
    }


async def _run_scan_job(job_id: str) -> None:
    async with SessionLocal() as db:
        job = await db.get(ScanJob, job_id)
        if job is None:
            return
        asset = await db.get(WebAsset, job.web_asset_id)
        if asset is None:
            job.status = "failed"
            job.error_message = "Web asset missing"
            job.completed_at = datetime.now(UTC)
            await db.commit()
            return
        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.current_tool = "subfinder"
        await db.commit()

        async def on_tool(tool: str) -> None:
            job.current_tool = tool
            await db.commit()

        try:
            result = await execute_scan(asset.domain, on_tool=on_tool)
            raw = result.get("raw_output") or {}
            tools = result.get("tools_run") or []
            tools_skipped = result.get("tools_skipped") or []
            status = result.get("status") or "completed"
            errors = result.get("errors") or []
            preparsed = result.get("findings") if isinstance(result.get("findings"), list) else None
            findings = normalize_raw(asset.domain, raw, preparsed=preparsed)
            events, alerts = await persist_web_findings(
                db,
                organization_id=job.organization_id,
                web_asset_id=asset.id,
                domain=asset.domain,
                findings=findings,
            )
            job.tools_run = tools
            job.raw_output = {
                "_tools_skipped": tools_skipped,
                **{k: (v[:50000] if isinstance(v, str) else v) for k, v in raw.items()},
            }
            job.findings_count = len(findings)
            job.status = status if status in {"completed", "failed", "timed_out"} else "completed"
            err_msg = result.get("error_message")
            if not err_msg and errors:
                err_msg = "; ".join(str(e) for e in errors)[:500]
            job.error_message = err_msg
            job.current_tool = None
            job.completed_at = datetime.now(UTC)

            # Hunter AI interpretation of the scan batch
            if findings:
                gateway = _gateway("hunter")
                await store_analysis(
                    db,
                    gateway,
                    organization_id=job.organization_id,
                    role="hunter_analysis",
                    subject_type="web_scan",
                    subject_id=job.id,
                    payload={
                        "domain": asset.domain,
                        "findings": [
                            {"title": f.get("title"), "severity": f.get("severity"), "tool": f.get("tool_source")}
                            for f in findings[:40]
                        ],
                    },
                )

            # Sentinel auto-triage on high/critical
            high = [a for a in alerts if a.severity in {"high", "critical"}]
            if high:
                gateway = _gateway("sentinel")
                await store_analysis(
                    db,
                    gateway,
                    organization_id=job.organization_id,
                    role="sentinel",
                    subject_type="web_scan",
                    subject_id=job.id,
                    payload={
                        "domain": asset.domain,
                        "findings": [
                            {"title": a.title, "severity": a.severity, "evidence": a.evidence_json}
                            for a in high
                        ],
                        "auto_detected": True,
                    },
                )
            await write_audit(
                db,
                action="web_asset.scan_complete",
                actor_id=job.requested_by_user_id,
                organization_id=job.organization_id,
                resource_type="scan_job",
                resource_id=job.id,
                details={"findings": len(findings), "status": job.status},
            )
            await db.commit()
        except Exception as exc:
            log.exception("Scan job %s failed", job_id)
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.completed_at = datetime.now(UTC)
            job.current_tool = None
            await db.commit()


@router.post("/web-assets/{asset_id}/scan", status_code=202)
async def start_scan(
    asset_id: str,
    payload: ScanPayload,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
    user: User = Depends(get_current_user),
) -> dict:
    asset = await _get_asset(db, asset_id, membership.organization_id)
    if asset.verification_status != "verified":
        raise HTTPException(status_code=403, detail="Domain must be verified before scanning")
    if (payload.role or "hunter").lower() != "hunter":
        raise HTTPException(status_code=400, detail="Only hunter role triggers a scan")

    running = (
        await db.execute(
            select(ScanJob).where(
                ScanJob.web_asset_id == asset.id,
                ScanJob.status.in_(("queued", "running")),
            )
        )
    ).scalars().first()
    if running is not None:
        raise HTTPException(status_code=429, detail="A scan is already running for this asset")

    limits = await org_limits(db, membership.organization_id)
    scan_limit = limits["scans_monthly"]
    if scan_limit is not None and await monthly_scan_count(db, membership.organization_id) >= scan_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly scan quota exceeded ({scan_limit} per 30 days on {limits['plan_name']}). Upgrade your plan for more scans.",
        )

    job = ScanJob(
        id=new_id(),
        web_asset_id=asset.id,
        organization_id=membership.organization_id,
        role="hunter",
        status="queued",
        tools_run=[],
        requested_by_user_id=user.id,
    )
    db.add(job)
    await write_audit(
        db,
        action="web_asset.scan_start",
        actor_id=user.id,
        organization_id=membership.organization_id,
        resource_type="scan_job",
        resource_id=job.id,
        details={"domain": asset.domain},
        ip_address=_client_ip(request),
    )
    await db.commit()
    background.add_task(_run_scan_job, job.id)
    return {"scan_job_id": job.id, "status": "queued"}


@router.get("/web-assets/{asset_id}/scans/{scan_job_id}")
async def get_scan_status(
    asset_id: str,
    scan_job_id: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> dict:
    await _get_asset(db, asset_id, membership.organization_id)
    job = await db.get(ScanJob, scan_job_id)
    if job is None or job.organization_id != membership.organization_id or job.web_asset_id != asset_id:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return {
        "id": job.id,
        "status": job.status,
        "tools_run": job.tools_run or [],
        "tools_skipped": (job.raw_output or {}).get("_tools_skipped", []),
        "current_tool": job.current_tool,
        "findings_count": job.findings_count,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/web-assets/{asset_id}/scans")
async def list_scans(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> list[dict]:
    await _get_asset(db, asset_id, membership.organization_id)
    rows = (
        await db.execute(
            select(ScanJob)
            .where(ScanJob.web_asset_id == asset_id, ScanJob.organization_id == membership.organization_id)
            .order_by(ScanJob.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        {
            "id": row.id,
            "status": row.status,
            "tools_run": row.tools_run or [],
            "tools_skipped": (row.raw_output or {}).get("_tools_skipped", []),
            "findings_count": row.findings_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in rows
    ]


@router.get("/web-assets/{asset_id}/findings")
async def list_findings(
    asset_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> list[dict]:
    await _get_asset(db, asset_id, membership.organization_id)
    alerts = (await _web_alerts_by_asset(db, membership.organization_id)).get(asset_id, [])
    out = []
    for row in alerts:
        evidence = row.evidence_json or {}
        out.append(
            {
                "id": row.id,
                "source": "web_asset",
                "source_id": asset_id,
                "title": row.title,
                "severity": row.severity,
                "tool_source": evidence.get("tool_source"),
                "confidence": row.confidence,
                "risk_score": row.risk_score,
                "detection_source": row.detection_source,
                "evidence": evidence,
                "recommended_next_step": row.recommended_next_step,
                "status": row.status,
                "auto_detected": bool((evidence or {}).get("auto_detected")),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
        if len(out) >= limit:
            break
    if out:
        return out
    # Fallback to raw events
    events = (
        await db.execute(
            select(SecurityEvent)
            .where(
                SecurityEvent.organization_id == membership.organization_id,
                SecurityEvent.source == "web_asset",
                SecurityEvent.source_id == asset_id,
            )
            .order_by(SecurityEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        {
            "id": row.id,
            "source": row.source,
            "source_id": row.source_id,
            "title": (row.payload_json or {}).get("title") or row.event_type,
            "severity": (row.payload_json or {}).get("severity") or "medium",
            "evidence": row.payload_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in events
    ]


@router.post("/web-assets/{asset_id}/evidence", status_code=201)
async def upload_asset_evidence(
    asset_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
    user: User = Depends(get_current_user),
) -> dict:
    asset = await _get_asset(db, asset_id, membership.organization_id)
    content_type = (file.content_type or "").lower()
    signatures = IMAGE_SIGNATURES.get(content_type)
    if signatures is None:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP image")
    content = await file.read(MAX_EVIDENCE_BYTES + 1)
    if len(content) > MAX_EVIDENCE_BYTES:
        raise HTTPException(status_code=413, detail="Evidence images must be 800 KB or smaller")
    valid_signature = content.startswith(signatures[0])
    if content_type == "image/webp":
        valid_signature = valid_signature and len(content) >= 12 and content[8:12] == b"WEBP"
    if not valid_signature:
        raise HTTPException(status_code=415, detail="Image content does not match its declared type")

    digest = hashlib.sha256(content).hexdigest()
    row = WebAssetEvidence(
        id=new_id(),
        organization_id=membership.organization_id,
        web_asset_id=asset.id,
        uploaded_by_user_id=user.id,
        filename=Path(file.filename or "evidence").name[:255],
        content_type=content_type,
        byte_size=len(content),
        sha256=digest,
        content=content,
        created_at=datetime.now(UTC),
    )
    db.add(row)
    await write_audit(
        db,
        action="web_asset.evidence_upload",
        actor_id=user.id,
        organization_id=membership.organization_id,
        resource_type="web_asset_evidence",
        resource_id=row.id,
        details={"web_asset_id": asset.id, "sha256": digest, "byte_size": len(content), "content_type": content_type},
        ip_address=_client_ip(request),
    )
    await db.commit()
    return {
        "id": row.id,
        "web_asset_id": asset.id,
        "filename": row.filename,
        "content_type": row.content_type,
        "byte_size": row.byte_size,
        "sha256": row.sha256,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/web-assets/{asset_id}/evidence")
async def list_asset_evidence(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> list[dict]:
    asset = await _get_asset(db, asset_id, membership.organization_id)
    rows = (
        await db.execute(
            select(WebAssetEvidence)
            .where(
                WebAssetEvidence.web_asset_id == asset.id,
                WebAssetEvidence.organization_id == membership.organization_id,
            )
            .order_by(WebAssetEvidence.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return [
        {
            "id": row.id,
            "filename": row.filename,
            "content_type": row.content_type,
            "byte_size": row.byte_size,
            "sha256": row.sha256,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/web-assets/{asset_id}/evidence/{evidence_id}")
async def get_asset_evidence_image(
    asset_id: str,
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> Response:
    asset = await _get_asset(db, asset_id, membership.organization_id)
    row = await db.get(WebAssetEvidence, evidence_id)
    if row is None or row.organization_id != membership.organization_id or row.web_asset_id != asset.id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return Response(
        content=row.content,
        media_type=row.content_type,
        headers={"Content-Disposition": "inline", "Cache-Control": "private, no-store"},
    )


CONFIDENCE_WORDS = {"very high": 0.95, "high": 0.85, "medium": 0.6, "moderate": 0.6, "low": 0.3, "very low": 0.15}


def _confidence(value: object) -> float:
    """LLMs return confidence as 0–1, 0–100, "85%", or words like "High"."""
    if isinstance(value, str):
        text = value.strip().lower()
        if text in CONFIDENCE_WORDS:
            return CONFIDENCE_WORDS[text]
        try:
            value = float(text.rstrip("%"))
        except ValueError:
            return 0.5
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 0.5
    score = float(value)
    if score > 1:
        score /= 100
    return max(0.0, min(1.0, score))


@router.post("/findings/{finding_id}/analyze")
async def analyze_finding(
    finding_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
    user: User = Depends(get_current_user),
) -> dict:
    alert = await db.get(Alert, finding_id)
    if alert is None or alert.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    analysis = await store_analysis(
        db,
        _gateway("analyst"),
        organization_id=membership.organization_id,
        role="analyst",
        subject_type="finding",
        subject_id=finding_id,
        payload={
            "title": alert.title,
            "severity": alert.severity,
            "evidence": alert.evidence_json,
        },
    )
    await write_audit(
        db,
        action="finding.analyze",
        actor_id=user.id,
        organization_id=membership.organization_id,
        resource_type="alert",
        resource_id=finding_id,
        ip_address=_client_ip(request),
    )
    await db.commit()
    output = analysis.output_json or {}
    return {
        "explanation": output.get("explanation") or output.get("summary") or "Analysis unavailable",
        "severity_assessment": output.get("severity_assessment") or output.get("priority") or alert.severity,
        "confidence": _confidence(output.get("confidence")),
        "analysis_id": analysis.id,
        "auto_detected": False,
    }


@router.post("/findings/{finding_id}/fix")
async def fix_finding(
    finding_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
    user: User = Depends(get_current_user),
) -> dict:
    alert = await db.get(Alert, finding_id)
    if alert is None or alert.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    analysis = await store_analysis(
        db,
        _gateway("fixer"),
        organization_id=membership.organization_id,
        role="fixer",
        subject_type="finding",
        subject_id=finding_id,
        payload={
            "title": alert.title,
            "severity": alert.severity,
            "evidence": alert.evidence_json,
        },
    )
    await write_audit(
        db,
        action="finding.fix",
        actor_id=user.id,
        organization_id=membership.organization_id,
        resource_type="alert",
        resource_id=finding_id,
        ip_address=_client_ip(request),
    )
    await db.commit()
    output = analysis.output_json or {}
    remediation = output.get("recommended_remediation") or []
    description = output.get("description") or output.get("explanation") or "Remediation draft"
    if isinstance(remediation, list) and remediation and not output.get("description"):
        description = "; ".join(str(x) for x in remediation[:3])
    return {
        "fix_type": output.get("fix_type") or "config_change",
        "description": description,
        "diff": output.get("diff") or output.get("patch") or "# Review manually — no automated patch generated\n",
        "requires_human_approval": True,
        "analysis_id": analysis.id,
        "applied": False,
    }


@router.post("/findings/{finding_id}/fix/open-pr")
async def open_fix_pr(
    finding_id: str,
    membership: Membership = Depends(require_rank("ADMIN")),
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="GitHub App integration is not configured. Fix drafts are stored but PRs must be opened manually.",
    )


@router.post("/web-assets/{asset_id}/report", status_code=202)
async def generate_report(
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(require_rank("SECURITY_ANALYST")),
    user: User = Depends(get_current_user),
) -> dict:
    asset = await _get_asset(db, asset_id, membership.organization_id)
    findings = await list_findings(asset_id, limit=100, db=db, membership=membership)
    analysis = await store_analysis(
        db,
        _gateway("auditor"),
        organization_id=membership.organization_id,
        role="auditor",
        subject_type="web_asset",
        subject_id=asset_id,
        payload={"domain": asset.domain, "findings": findings},
    )
    body = (analysis.output_json or {}).get("explanation") or (analysis.output_json or {}).get("report") or ""
    if isinstance(body, dict):
        body = str(body)
    report = Report(
        id=new_id(),
        organization_id=membership.organization_id,
        title=f"Security report — {asset.domain}",
        body_markdown=str(body),
        created_by_user_id=user.id,
    )
    db.add(report)
    await write_audit(
        db,
        action="web_asset.report",
        actor_id=user.id,
        organization_id=membership.organization_id,
        resource_type="report",
        resource_id=report.id,
        details={"web_asset_id": asset_id},
        ip_address=_client_ip(request),
    )
    await db.commit()
    return {"report_job_id": report.id, "status": "completed", "report_id": report.id}


@router.get("/web-assets/{asset_id}/report/{report_id}")
async def get_report(
    asset_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    membership: Membership = Depends(get_membership),
) -> dict:
    await _get_asset(db, asset_id, membership.organization_id)
    report = await db.get(Report, report_id)
    if report is None or report.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": report.id,
        "title": report.title,
        "body_markdown": report.body_markdown,
        "status": "completed",
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
