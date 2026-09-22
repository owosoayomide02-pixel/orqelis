from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from orqelis_agent.common import event


def defender_status() -> str:
    """Linux has no Defender; report not applicable so scoring does not penalize it."""
    return "n/a"


def firewall_status() -> str:
    try:
        ufw = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=8, check=False)
        text = (ufw.stdout or "").lower()
        if ufw.returncode == 0 and "status: active" in text:
            return "on"
        if ufw.returncode == 0 and "status: inactive" in text:
            return "off"
        firewalld = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True, timeout=8, check=False)
        if "running" in (firewalld.stdout or "").lower():
            return "on"
        return "unknown"
    except Exception:
        return "unknown"


def can_read_security_log() -> bool:
    for path in (Path("/var/log/auth.log"), Path("/var/log/secure")):
        if path.exists() and os.access(path, os.R_OK):
            return True
    try:
        completed = subprocess.run(["journalctl", "-n", "1", "--no-pager"], capture_output=True, text=True, timeout=8, check=False)
        return completed.returncode == 0
    except Exception:
        return False


def security_events() -> list[dict[str, Any]]:
    lines: list[str] = []
    for path in (Path("/var/log/auth.log"), Path("/var/log/secure")):
        if path.exists() and os.access(path, os.R_OK):
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-40:]
                break
            except OSError:
                continue
    if not lines:
        try:
            completed = subprocess.run(
                ["journalctl", "-n", "40", "--no-pager", "-q"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if completed.returncode == 0:
                lines = (completed.stdout or "").splitlines()[-40:]
        except Exception:
            lines = []
    events = [event("linux_auth", "snapshot", {"lines": min(len(lines), 40), "source": "auth-log-or-journal"})]
    failures = [line for line in lines if "failed password" in line.lower() or "authentication failure" in line.lower()]
    for line in failures[-8:]:
        events.append(event("authentication", "auth_failure", {"summary": line[:180]}))
    successes = [line for line in lines if "accepted password" in line.lower() or "session opened" in line.lower()]
    for line in successes[-5:]:
        events.append(event("authentication", "auth_success", {"summary": line[:180]}))
    return events


def service_state() -> list[dict[str, Any]]:
    names = ["ssh", "sshd", "ufw", "firewalld", "cron"]
    services = []
    try:
        completed = subprocess.run(["systemctl", "is-active", *names], capture_output=True, text=True, timeout=8, check=False)
        statuses = (completed.stdout or "").strip().splitlines()
        for name, status in zip(names, statuses):
            services.append({"name": name, "status": status})
    except Exception:
        return [event("service", "snapshot", {"services": [], "platform": "linux"})]
    return [event("service", "snapshot", {"services": services, "platform": "linux"})]
