from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_privacy_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
    devices: Mapped[list["Device"]] = relationship(back_populates="organization")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="OWNER")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_agent: Mapped[str] = mapped_column(String(400), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="sessions")


class EmailToken(Base):
    __tablename__ = "email_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), index=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InternalUser(Base):
    __tablename__ = "internal_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(32), default="FOUNDER")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InternalSession(Base):
    __tablename__ = "internal_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    internal_user_id: Mapped[str] = mapped_column(ForeignKey("internal_users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    monthly_price_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    contact_sales: Mapped[bool] = mapped_column(Boolean, default=False)
    features_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), unique=True, index=True)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="none")
    provider: Mapped[str] = mapped_column(String(32), default="development")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    hostname: Mapped[str] = mapped_column(String(160), default="")
    os_name: Mapped[str] = mapped_column(String(80), default="Windows")
    os_version: Mapped[str] = mapped_column(String(80), default="")
    agent_version: Mapped[str] = mapped_column(String(32), default="0.1.0")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    token_hash: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_json: Mapped[dict] = mapped_column(JSON, default=dict)
    posture_json: Mapped[dict] = mapped_column(JSON, default=dict)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="devices")
    enrollments: Mapped[list["DeviceEnrollment"]] = relationship(back_populates="device")


class DeviceEnrollment(Base):
    __tablename__ = "device_enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    code_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    device: Mapped[Device | None] = relationship(back_populates="enrollments")


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("version", "platform", name="uq_agent_version_platform"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version: Mapped[str] = mapped_column(String(32), index=True)
    platform: Mapped[str] = mapped_column(String(32), default="windows")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), default="Default")
    collect_process_metadata: Mapped[bool] = mapped_column(Boolean, default=True)
    collect_security_events: Mapped[bool] = mapped_column(Boolean, default=True)
    collect_network_metadata: Mapped[bool] = mapped_column(Boolean, default=True)
    heartbeat_seconds: Mapped[int] = mapped_column(Integer, default=30)
    batch_max_events: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SecurityEvent(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    severity: Mapped[str] = mapped_column(String(32), default="low")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    risk_score: Mapped[int] = mapped_column(Integer, default=10)
    detection_source: Mapped[str] = mapped_column(String(32), default="rule")
    rule_id: Mapped[str] = mapped_column(String(80), default="")
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    recommended_next_step: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="open")
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="open")
    risk_score: Mapped[int] = mapped_column(Integer, default=40)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    alert_id: Mapped[str | None] = mapped_column(ForeignKey("alerts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="open")
    source: Mapped[str] = mapped_column(String(32), default="posture")
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    requested_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action_id: Mapped[str | None] = mapped_column(ForeignKey("actions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    reason: Mapped[str] = mapped_column(Text, default="")
    risk_class: Mapped[str] = mapped_column(String(32), default="high")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    decided_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActionRecord(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(240))
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_class: Mapped[str] = mapped_column(String(32), default="low")
    status: Mapped[str] = mapped_column(String(32), default="recommended")
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentCommand(Base):
    __tablename__ = "agent_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="analyst")
    subject_type: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[str] = mapped_column(String(36), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="heuristic")
    model: Mapped[str] = mapped_column(String(80), default="")
    input_redacted_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="heuristic")
    model: Mapped[str] = mapped_column(String(80), default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    body_markdown: Mapped[str] = mapped_column(Text, default="")
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="available")
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="user")
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), default="")
    resource_id: Mapped[str] = mapped_column(String(36), default="")
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class SystemIncident(Base):
    __tablename__ = "system_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32), default="open")
    severity: Mapped[str] = mapped_column(String(32), default="low")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DemoWorkspace(Base):
    """Marks an organization as labeled demo data. Never mix with live agent telemetry."""

    __tablename__ = "demo_workspaces"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    label: Mapped[str] = mapped_column(String(160), default="LABELED DEMO — not live telemetry")
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
