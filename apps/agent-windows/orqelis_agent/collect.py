from __future__ import annotations

import os
import platform
import socket
from typing import Any

import psutil

from orqelis_agent.common import AGENT_VERSION, event
from orqelis_agent.platforms import linux as linux_platform
from orqelis_agent.platforms import macos as macos_platform
from orqelis_agent.platforms import windows as windows_platform


def _impl():
    name = platform.system()
    if name == "Windows":
        return windows_platform
    if name == "Darwin":
        return macos_platform
    return linux_platform


def health() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    impl = _impl()
    return {
        "agent_version": AGENT_VERSION,
        "pid": os.getpid(),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": vm.percent,
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "running_as_admin": _is_admin(),
        "can_read_security_log": impl.can_read_security_log(),
    }


def posture() -> dict[str, Any]:
    impl = _impl()
    return {
        "defender_status": impl.defender_status(),
        "firewall_status": impl.firewall_status(),
        "platform": platform.system(),
    }


def collect_batch(policy: dict[str, Any]) -> list[dict[str, Any]]:
    impl = _impl()
    events: list[dict[str, Any]] = [
        event("device_info", "inventory", _device_info()),
        event("agent_health", "heartbeat", health()),
        event("security_control", "posture", posture()),
    ]
    if policy.get("collect_process_metadata", True):
        events.append(event("process", "snapshot", {"processes": _processes()}))
    if policy.get("collect_network_metadata", True):
        events.append(event("network", "snapshot", {"connections": _connections()}))
    if policy.get("collect_security_events", True):
        events.extend(impl.security_events())
    events.extend(impl.service_state())
    return events


def _device_info() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "os_name": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "agent_version": AGENT_VERSION,
        "cpu_count": psutil.cpu_count() or 0,
    }


def _processes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "username", "exe", "ppid"]):
        info = proc.info
        rows.append(
            {
                "pid": info.get("pid"),
                "name": info.get("name") or "",
                "user": info.get("username") or "",
                "path": info.get("exe") or "",
                "ppid": info.get("ppid"),
            }
        )
        if len(rows) >= 200:
            break
    return rows


def _connections() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if not conn.raddr:
                continue
            rows.append(
                {
                    "pid": conn.pid,
                    "status": conn.status,
                    "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                    "remote_addr": conn.raddr.ip,
                    "remote_port": conn.raddr.port,
                }
            )
            if len(rows) >= 80:
                break
    except (psutil.AccessDenied, PermissionError):
        return []
    return rows


def _is_admin() -> bool:
    if os.name != "nt":
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
