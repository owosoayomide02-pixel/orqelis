CUSTOMER_ROLE_RANK = {
    "VIEWER": 1,
    "SECURITY_ANALYST": 2,
    "ADMIN": 3,
    "OWNER": 4,
}

WRITE_ROLES = {"OWNER", "ADMIN", "SECURITY_ANALYST"}
ADMIN_ROLES = {"OWNER", "ADMIN"}
APPROVER_ROLES = {"OWNER", "ADMIN"}

# Agent telemetry allowlist — do not expand without a product + privacy review.
ALLOWED_EVENT_CATEGORIES = {
    "device_info",
    "process",
    "authentication",
    "windows_security",
    "service",
    "network",
    "security_control",
    "agent_health",
}

AI_ROLES = ("sentinel", "hunter", "analyst", "auditor", "fixer")
