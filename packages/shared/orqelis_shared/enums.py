from enum import Enum


class CustomerRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    VIEWER = "VIEWER"


class InternalRole(str, Enum):
    FOUNDER = "FOUNDER"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    SUPPORT = "SUPPORT"


class DeviceStatus(str, Enum):
    PENDING = "pending"
    ONLINE = "online"
    OFFLINE = "offline"
    REVOKED = "revoked"


class EventCategory(str, Enum):
    DEVICE_INFO = "device_info"
    PROCESS = "process"
    AUTHENTICATION = "authentication"
    WINDOWS_SECURITY = "windows_security"
    SERVICE = "service"
    NETWORK = "network"
    SECURITY_CONTROL = "security_control"
    AGENT_HEALTH = "agent_health"


class AlertSeverity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionSource(str, Enum):
    RULE = "rule"
    CORRELATION = "correlation"
    POSTURE = "posture"
    AI = "ai"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionStatus(str, Enum):
    RECOMMENDED = "recommended"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    VERIFIED = "verified"


class AgentCommandKind(str, Enum):
    REFRESH_POLICY = "refresh_policy"
    RESTART_AGENT = "restart_agent"


class SubscriptionStatus(str, Enum):
    NONE = "none"
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class EmailBackend(str, Enum):
    LOG = "log"
    SMTP = "smtp"
