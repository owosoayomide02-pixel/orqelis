from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentVersion, Plan, new_id

DEFAULT_PLANS = [
    {
        "code": "personal",
        "name": "Personal",
        "description": "For individuals protecting computers they own.",
        "monthly_price_cents": 2000,
        "contact_sales": False,
        "features_json": [
            "Windows, macOS, and Linux endpoint agents",
            "Detection engine",
            "AI explanations",
            "Security reports",
        ],
    },
    {
        "code": "business_core",
        "name": "Business Core",
        "description": "For small teams that need centralized endpoint security.",
        "monthly_price_cents": 50000,
        "contact_sales": False,
        "features_json": [
            "Multiple Windows, macOS, and Linux endpoints",
            "Role-based access",
            "Incident correlation",
            "AI Security Team workflows",
        ],
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Custom security, retention, and support commitments.",
        "monthly_price_cents": 0,
        "contact_sales": True,
        "features_json": [
            "Custom terms",
            "Dedicated support",
            "Advanced retention",
            "Contact sales",
        ],
    },
]


async def seed_reference_data(db: AsyncSession) -> None:
    for item in DEFAULT_PLANS:
        existing = (await db.execute(select(Plan).where(Plan.code == item["code"]))).scalar_one_or_none()
        if existing is None:
            db.add(Plan(id=new_id(), **item, currency="USD", is_public=True))
    for platform, notes in (
        ("windows", "Windows endpoint agent. Telemetry only; no remote command execution."),
        ("macos", "macOS endpoint agent. Gatekeeper/firewall posture plus process and network metadata."),
        ("linux", "Linux endpoint agent. Auth log/journal telemetry plus host firewall posture."),
    ):
        existing = (
            await db.execute(select(AgentVersion).where(AgentVersion.version == "0.1.0", AgentVersion.platform == platform))
        ).scalar_one_or_none()
        if existing is None:
            db.add(AgentVersion(id=new_id(), version="0.1.0", platform=platform, notes=notes))
    await db.commit()
