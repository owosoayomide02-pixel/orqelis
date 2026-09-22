from __future__ import annotations

from pathlib import Path

from app.models import AgentVersion

REPO_ROOT = Path(__file__).resolve().parents[3]

PLATFORM_FILES = {
    "windows": REPO_ROOT / "apps" / "agent-windows" / "dist" / "orqelis-agent-windows.exe",
    "macos": REPO_ROOT / "apps" / "agent-windows" / "dist" / "orqelis-agent-macos",
    "linux": REPO_ROOT / "apps" / "agent-windows" / "dist" / "orqelis-agent-linux",
}

PLATFORM_LABELS = {
    "windows": "Windows",
    "macos": "macOS",
    "linux": "Linux",
}


def enroll_commands(platform: str, api_url: str) -> str:
    api = api_url.rstrip("/")
    if platform == "windows":
        return (
            "cd orqelis\\apps\\agent-windows\n"
            f"python -m orqelis_agent enroll --code YOURCODE --api {api}\n"
            "python -m orqelis_agent run"
        )
    return (
        "cd orqelis/apps/agent-windows\n"
        f"python3 -m orqelis_agent enroll --code YOURCODE --api {api}\n"
        "python3 -m orqelis_agent run"
    )


def package_command(platform: str) -> str:
    if platform == "windows":
        return ".\\scripts\\package-windows.ps1"
    if platform == "macos":
        return "./scripts/package-macos.sh"
    return "./scripts/package-linux.sh"


def catalog(versions: list[AgentVersion], api_url: str) -> list[dict]:
    by_platform = {row.platform: row for row in versions}
    rows = []
    for platform in ("windows", "macos", "linux"):
        path = PLATFORM_FILES[platform]
        version = by_platform.get(platform)
        rows.append(
            {
                "platform": platform,
                "label": PLATFORM_LABELS[platform],
                "version": version.version if version else "0.1.0",
                "notes": version.notes if version else "",
                "binary_available": path.is_file(),
                "filename": path.name,
                "download_path": f"/api/v1/devices/agent-downloads/{platform}" if path.is_file() else None,
                "package_command": package_command(platform),
                "enroll_commands": enroll_commands(platform, api_url),
                "notice": "Telemetry only. The agent does not execute arbitrary remote commands.",
            }
        )
    return rows


def binary_path(platform: str) -> Path | None:
    path = PLATFORM_FILES.get(platform)
    if path is None or not path.is_file():
        return None
    return path
