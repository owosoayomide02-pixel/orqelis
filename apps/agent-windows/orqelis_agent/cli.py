from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

from orqelis_agent.collect import collect_batch
from orqelis_agent.config import AgentConfig, default_api_url, load_config, save_config
from orqelis_agent.transport import AgentClient

NOTICE = """
Orqelis Endpoint Security

This software collects security telemetry necessary to provide endpoint
protection and security monitoring.

The information collected may include device information, security events,
process metadata, and other security telemetry described in the Orqelis
Privacy Policy.

By installing this agent, you confirm that you are authorized to install
and operate it on this device.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orqelis-agent", description="Orqelis endpoint agent for Windows, macOS, and Linux")
    sub = parser.add_subparsers(dest="command", required=True)
    enroll = sub.add_parser("enroll", help="Enroll this device with a one-time code")
    enroll.add_argument("--code", required=True)
    enroll.add_argument("--api", default=default_api_url())
    sub.add_parser("run", help="Start telemetry collection")
    sub.add_parser("status", help="Show local agent status")
    args = parser.parse_args(argv)

    if args.command == "enroll":
        print(NOTICE)
        config = AgentConfig(api_url=args.api.rstrip("/"))
        client = AgentClient(config)
        try:
            result = client.enroll(args.code)
        except httpx.RequestError:
            print(f"Could not reach the Orqelis API at {config.api_url}.", file=sys.stderr)
            print("Pass --api with the live API URL, or set ORQELIS_API_URL.", file=sys.stderr)
            return 1
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail") or ""
            except Exception:
                detail = (exc.response.text or "")[:200]
            print(f"Enrollment failed ({exc.response.status_code}): {detail or exc}", file=sys.stderr)
            print("Create a fresh code in Devices and try again.", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"The Orqelis API at {config.api_url} failed: {exc}", file=sys.stderr)
            print("Try again in a moment, or pass --api with a reachable URL.", file=sys.stderr)
            return 1
        config.api_url = args.api.rstrip("/")
        config.device_id = result["device_id"]
        config.device_token = result["device_token"]
        save_config(config)
        print("Enrolled device", result["device_id"])
        print(result.get("notice") or "")
        return 0
    if args.command == "status":
        config = load_config()
        print(json.dumps({"device_id": config.device_id, "api_url": config.api_url, "enrolled": bool(config.device_token)}, indent=2))
        return 0
    if args.command == "run":
        config = load_config()
        if not config.device_token:
            print("Device is not enrolled. Run: python -m orqelis_agent enroll --code NNNNNN", file=sys.stderr)
            return 1
        print("Orqelis agent running. Telemetry only. Ctrl+C to stop.")
        client = AgentClient(config)
        while True:
            try:
                policy = client.heartbeat()
                interval = int((policy.get("policy") or {}).get("heartbeat_seconds") or 30)
                events = collect_batch(policy.get("policy") or {})
                if events:
                    client.send_events(events)
                commands = policy.get("commands") or []
                acked = []
                for command in commands:
                    kind = command.get("kind")
                    if kind in {"refresh_policy", "restart_agent"}:
                        # Policy refresh is a no-op beyond the next heartbeat.
                        # Restart is a local process exit; the service manager / user restarts it.
                        acked.append(command["id"])
                        if kind == "restart_agent":
                            client.ack(acked)
                            print("Restart command acknowledged. Exiting agent process.")
                            return 0
                if acked:
                    client.ack(acked)
                time.sleep(max(10, interval))
            except KeyboardInterrupt:
                return 0
            except Exception as exc:
                print("agent error:", exc, file=sys.stderr)
                time.sleep(15)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
