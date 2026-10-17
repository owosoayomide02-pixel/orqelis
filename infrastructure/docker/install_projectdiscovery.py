"""Install the latest Linux AMD64 ProjectDiscovery release binaries."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


TOOLS = ("subfinder", "httpx", "nuclei", "tlsx", "katana", "dnsx")
USER_AGENT = "Orqelis-scanner-image-builder"


def request(url: str, accept: str | None = None):
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    return urllib.request.Request(url, headers=headers)


def install_tool(tool: str, destination: Path) -> None:
    api_url = f"https://api.github.com/repos/projectdiscovery/{tool}/releases/latest"
    with urllib.request.urlopen(request(api_url, "application/vnd.github+json"), timeout=60) as response:
        release = json.load(response)

    asset_name = f"{tool}_{release['tag_name'].lstrip('v')}_linux_amd64.zip"
    asset = next((item for item in release.get("assets", []) if item.get("name") == asset_name), None)
    if not asset:
        raise RuntimeError(f"No Linux AMD64 release asset found for {tool}: {asset_name}")

    with tempfile.TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / asset_name
        with urllib.request.urlopen(request(asset["browser_download_url"]), timeout=180) as response:
            with archive_path.open("wb") as archive_file:
                shutil.copyfileobj(response, archive_file)

        expected_digest = asset.get("digest") or ""
        if expected_digest.startswith("sha256:"):
            actual_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            if actual_digest != expected_digest.removeprefix("sha256:"):
                raise RuntimeError(f"SHA-256 mismatch for {tool} release asset")

        with zipfile.ZipFile(archive_path) as archive:
            binary = next((name for name in archive.namelist() if Path(name).name == tool), None)
            if not binary:
                raise RuntimeError(f"No {tool} executable found in {asset_name}")
            target = destination / tool
            with archive.open(binary) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/local/bin")
    destination.mkdir(parents=True, exist_ok=True)
    for tool in TOOLS:
        install_tool(tool, destination)


if __name__ == "__main__":
    main()