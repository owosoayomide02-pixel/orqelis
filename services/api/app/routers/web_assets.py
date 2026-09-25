"""Web asset management, DNS verification, Hunter scans, and AI role actions."""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
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
    WebAsset,
    new_id,
)
from app.scanner import execute_scan, normalize_raw
from orqelis_ai.gateway import AIGateway

log = logging.getLogger("orqelis.web_assets")
router = APIRouter(prefix="/api/v1", tags=["web-assets"])


def _gateway(role: str = "analyst") -> AIGateway:
    return AIGateway(
        provider=settings.resolved_ai_provider,
        api_key=settings.resolved_ai_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        model_light=settings.ai_model_light,
        model_heavy=settings.ai_model_heavy,
    )


def _verification_instructions(asset: WebAsset) -> dict[str, str]:
    return {
        "record_type": "TXT",
        "record_name": f"_orqelis-verify.{asset.domain}",
        "record_value": f"orqelis-verify={asset.verification_token}",
    }


def _asset_out(asset: WebAsset, *, include_instructions: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": asset.id,
        "domain": asset.domain,
        "verification_status": asset.verification_status,
        "verification_method": asset.verification_method,
        "verified_at": asset.verified_at.isoformat() if asset.verified_at else None,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "archived": asset.archived,
    }
    if include_instructions or asset.verification_status != "verified":
        data["verification_instructions"] = _verification_instructions(asset)
    return data


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
    return [_asset_out(row) for row in rows]


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
    return _asset_out(asset, include_instructions=True)


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
    if asset.last_verify_attempt_at:
        elapsed = (now - asset.last_verify_attempt_at).total_seconds()
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


async def _monthly_scan_count(db: AsyncSession, organization_id: str) -> int:
    since = datetime.now(UTC) - timedelta(days=30)
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(ScanJob)
                .where(ScanJob.organization_id == organization_id, ScanJob.created_at >= since)
            )
        ).scalar_one()
        or 0
    )


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

        try:
            result = await execute_scan(asset.domain)
            raw = result.get("raw_output") or {}
            tools = result.get("tools_run") or []
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
            job.raw_output = {k: (v[:50000] if isinstance(v, str) else v) for k, v in raw.items()}
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

    used = await _monthly_scan_count(db, membership.organization_id)
    if used >= settings.scan_quota_per_org_monthly:
        raise HTTPException(status_code=429, detail="Organization monthly scan quota exceeded")

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
    # Prefer alerts created from hunter for this asset
    alerts = (
        await db.execute(
            select(Alert)
            .where(Alert.organization_id == membership.organization_id)
            .order_by(Alert.created_at.desc())
            .limit(limit * 2)
        )
    ).scalars().all()
    out = []
    for row in alerts:
        evidence = row.evidence_json or {}
        if evidence.get("web_asset_id") != asset_id:
            continue
        out.append(
            {
                "id": row.id,
                "source": "web_asset",
                "source_id": asset_id,
                "title": row.title,
                "severity": row.severity,
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
        "confidence": float(output.get("confidence") or 0.5),
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
