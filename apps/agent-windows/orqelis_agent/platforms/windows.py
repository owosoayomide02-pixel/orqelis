from __future__ import annotations

import json
import subprocess
from typing import Any

import psutil

from orqelis_agent.common import event


def defender_status() -> str:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-MpComputerStatus).AMServiceEnabled"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        text = (completed.stdout or "").strip().lower()
        if text == "true":
            return "on"
        if text == "false":
            return "off"
        return "unknown"
    except Exception:
        return "unknown"


def firewall_status() -> str:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-NetFirewallProfile | Where-Object {$_.Enabled -eq $true} | Measure-Object).Count",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        count = int((completed.stdout or "0").strip() or 0)
        return "on" if count > 0 else "off"
    except Exception:
        return "unknown"


def can_read_security_log() -> bool:
    try:
        completed = subprocess.run(["wevtutil", "gli", "Security"], capture_output=True, text=True, timeout=8, check=False)
        return completed.returncode == 0
    except Exception:
        return False


def security_events() -> list[dict[str, Any]]:
    ids = "4624,4625,4672,4720"
    try:
        completed = subprocess.run(
            [
                "wevtutil",
                "qe",
                "Security",
                f"/q:*[System[(EventID={ids.replace(',', ' or EventID=')})]]",
                "/c:20",
                "/f:json",
                "/rd:true",
            ],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return [event("windows_security", "unavailable", {"reason": "Security log not readable", "returncode": completed.returncode})]
        raw = completed.stdout.strip()
        try:
            parsed = json.loads(raw if raw.startswith("[") else f"[{raw}]")
        except json.JSONDecodeError:
            return [event("windows_security", "parse_error", {"length": len(raw)})]
        events = []
        for item in parsed[:20]:
            system = item.get("Event", item).get("System", {}) if isinstance(item, dict) else {}
            event_id = str(system.get("EventID", {}).get("#text", system.get("EventID", "unknown")))
            events.append(event("windows_security", event_id, {"event_id": event_id}))
            if event_id == "4625":
                events.append(event("authentication", "auth_failure", {"event_id": event_id}))
            if event_id == "4624":
                events.append(event("authentication", "auth_success", {"event_id": event_id}))
        return events
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return [event("windows_security", "unavailable", {"reason": str(exc)[:200]})]


def service_state() -> list[dict[str, Any]]:
    names = ["WinDefend", "mpssvc", "EventLog", "wuauserv"]
    services = []
    try:
        for svc in psutil.win_service_iter():
            if svc.name() in names:
                services.append({"name": svc.name(), "status": svc.status(), "display": svc.display_name()})
    except Exception:
        return [event("service", "snapshot", {"services": [], "error": "unavailable", "platform": "windows"})]
    return [event("service", "snapshot", {"services": services, "platform": "windows"})]
