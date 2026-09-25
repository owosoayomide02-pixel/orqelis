"""Domain validation for web-asset scanning (SSRF / ownership guards)."""

from __future__ import annotations

import ipaddress
import re
import socket

DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)


def normalize_domain(raw: str) -> str:
    value = (raw or "").strip().lower()
    value = value.removeprefix("https://").removeprefix("http://")
    value = value.split("/")[0].split("?")[0].split("#")[0]
    if value.endswith("."):
        value = value[:-1]
    return value


def is_ip_literal(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def is_private_or_local_ip(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_domain(raw: str) -> str:
    """Return normalized domain or raise ValueError with a customer-facing message."""
    domain = normalize_domain(raw)
    if not domain:
        raise ValueError("Domain is required")
    if is_ip_literal(domain):
        raise ValueError("IP addresses are not allowed — provide a public domain name")
    if not DOMAIN_RE.match(domain):
        raise ValueError("Invalid domain format")
    # Block obvious internal hostnames
    labels = domain.split(".")
    if labels[-1] in {"local", "localhost", "internal", "lan", "corp", "home"}:
        raise ValueError("Internal or private domains are not allowed")
    if domain in {"localhost"} or domain.endswith(".localhost"):
        raise ValueError("Internal or private domains are not allowed")
    return domain


def domain_resolves_to_private(domain: str) -> bool:
    """Return True if resolution fails closed (unresolvable) or hits a private address."""
    try:
        infos = socket.getaddrinfo(domain, None)
    except OSError:
        # Fail closed for scan gating: treat unresolvable as unsafe to scan.
        return True
    if not infos:
        return True
    for info in infos:
        host = info[4][0]
        if is_private_or_local_ip(host):
            return True
    return False


def filter_public_hosts(hosts: list[str]) -> list[str]:
    """Drop hosts that resolve to private/link-local addresses (SSRF defense)."""
    public: list[str] = []
    for host in hosts:
        host = (host or "").strip().lower()
        if not host or is_ip_literal(host):
            continue
        if domain_resolves_to_private(host):
            continue
        public.append(host)
    return public
