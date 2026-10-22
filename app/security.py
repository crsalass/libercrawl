"""Local-only local extraction backend and public-site input validation.

The upstream engine additionally checks internal address access. DNS rebinding and
complex redirect flows are not completely preventable at this application layer.
Keep the whole system bound to loopback and do not expose it to untrusted users.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlsplit

LOCAL_ENGINE_HOSTS = {"127.0.0.1", "localhost", "::1"}
BLOCKED_SUFFIXES = (".local", ".localhost", ".internal", ".test", ".invalid", ".home", ".lan")
_HOSTNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$", re.I)


def validate_engine_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_ENGINE_HOSTS:
        raise ValueError("local extraction backend must be a local HTTP endpoint (localhost or 127.0.0.1).")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("Use a bare local local extraction endpoint without credentials, paths or query parameters.")
    if parsed.port is None or not (1 <= parsed.port <= 65535):
        raise ValueError("local extraction backend must declare its local port.")
    authority = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
    return f"http://{authority}:{parsed.port}"


def validate_target(url: str, *, resolve_dns: bool = True) -> str:
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("URL must be a string no longer than 2048 characters.")
    value = url.strip()
    p = urlsplit(value)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Only public HTTP or HTTPS website URLs are supported.")
    if p.username or p.password or p.fragment:
        raise ValueError("URLs must not contain credentials or fragments.")
    if p.port not in (None, 80, 443):
        raise ValueError("Only standard HTTP/HTTPS ports are permitted.")
    hostname = p.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(BLOCKED_SUFFIXES) or hostname.endswith(".onion"):
        raise ValueError("Local, internal and special-use hostnames are blocked.")
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        addr = None
    if addr is not None:
        raise ValueError("IP address targets are not supported; use a public domain name.")
    if not _HOSTNAME_RE.fullmatch(hostname) or "." not in hostname or ".." in hostname:
        raise ValueError("A valid public domain name is required.")
    if resolve_dns:
        try:
            addresses = socket.getaddrinfo(hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError(f"Domain lookup failed: {hostname}") from exc
        if not addresses:
            raise ValueError("Domain has no address records.")
        for record in addresses:
            ip = ipaddress.ip_address(record[4][0])
            if not ip.is_global:
                raise ValueError("Target domain resolves to a non-public address.")
    return value
