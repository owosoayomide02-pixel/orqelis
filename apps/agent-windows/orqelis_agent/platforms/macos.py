from __future__ import annotations

import subprocess
from typing import Any

from orqelis_agent.common import event


def defender_status() -> str:
    """Map Gatekeeper to the endpoint-protection posture field."""
    try:
        completed = subprocess.run(["spctl", "--status"], capture_output=True, text=True, timeout=8, check=False)
        text = (completed.stdout or completed.stderr or "").lower()
        if "enabled" in text:
            return "on"
        if "disabled" in text:
            return "off"
        return "unknown"
    except Exception:
        return "unknown"


def firewall_status() -> str:
    try:
        completed = subprocess.run(
            ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        text = (completed.stdout or "").lower()
        if "enabled" in text:
            return "on"
        if "disabled" in text:
            return "off"
        return "unknown"
    except Exception:
        return "unknown"


def can_read_security_log() -> bool:
    try:
        completed = subprocess.run(
            ["log", "show", "--style", "syslog", "--last", "1m", "--predicate", "eventMessage CONTAINS \"error\""],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return completed.returncode == 0
    except Exception:
        return False


def security_events() -> list[dict[str, Any]]:
    try:
        completed = subprocess.run(
            ["log", "show", "--style", "compact", "--last", "10m", "--predicate", 'eventMessage CONTAINS[c] "failed" OR eventMessage CONTAINS[c] "authentication"'],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        if completed.returncode != 0:
            return [event("macos_security", "unavailable", {"reason": "unified log not readable"})]
        lines = (completed.stdout or "").splitlines()[-30:]
        events = [event("macos_security", "snapshot", {"lines": len(lines)})]
        for line in lines:
            lowered = line.lower()
            if "fail" in lowered:
                events.append(event("authentication", "auth_failure", {"summary": line[:180]}))
        return events
    except Exception as exc:
        return [event("macos_security", "unavailable", {"reason": str(exc)[:200]})]


def service_state() -> list[dict[str, Any]]:
    services = []
    try:
        completed = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=8, check=False)
        interesting = ("com.apple.securityd", "com.apple.WindowServer", "com.openssh.sshd")
        for line in (completed.stdout or "").splitlines():
            if any(name in line for name in interesting):
                services.append({"raw": line[:160]})
    except Exception:
        return [event("service", "snapshot", {"services": [], "platform": "macos"})]
    return [event("service", "snapshot", {"services": services, "platform": "macos"})]
