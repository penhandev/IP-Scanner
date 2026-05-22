"""Parse target strings into normalized :class:`Target` records.

Supports:
    * single IPv4/IPv6 addresses     e.g. ``8.8.8.8``
    * CIDR notation                  e.g. ``10.0.0.0/24``
    * IPv4 ranges                    e.g. ``1.1.1.1-1.1.1.50``
    * bare domains                   e.g. ``github.com``
    * domains with ``www.`` prefix   e.g. ``www.github.com``
    * full URLs                      e.g. ``https://api.github.com/v3``
    * host:port pairs                e.g. ``1.1.1.1:443``

Lines starting with ``#`` and blank lines are skipped.
"""

from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse


@dataclass(frozen=True)
class Target:
    """A normalized scan target.

    Attributes:
        original: The input string as written in the source file
                  (preserved so the user recognizes their input).
        host: The host part used for TCP/HTTP checks
              (a hostname or an IP literal).
        ip: The resolved IPv4/IPv6 address; ``None`` if DNS failed
            or resolution was skipped.
    """

    original: str
    host: str
    ip: Optional[str]

    @property
    def display(self) -> str:
        """A human-friendly representation for the UI."""
        if self.ip is None:
            return f"{self.original} [unresolved]"
        if self.host == self.ip:
            return self.original
        return f"{self.original} -> {self.ip}"

    @property
    def output_label(self) -> str:
        """Label used when writing this target to the alive-targets TXT.

        For CIDR / range expansions, writing the original (``1.0.0.0/24``)
        once per expanded host produces duplicates, so we fall back to the
        IP. For explicit inputs (single IPs, domains, URLs) the original
        string is preserved.
        """
        if self.original != self.host and self.host == self.ip:
            return self.host
        return self.original


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _resolve(host: str) -> Optional[str]:
    """Resolve a hostname to its first IPv4 address, or ``None`` on failure."""
    try:
        return socket.gethostbyname(host)
    except (socket.gaierror, socket.herror, OSError):
        return None


def _normalize_url_or_domain(raw: str) -> Tuple[str, str]:
    """Return ``(original, host)`` for URL / domain / ``host:port`` input."""
    original = raw
    target = raw

    if target.startswith(("http://", "https://")):
        parsed = urlparse(target)
        if parsed.hostname:
            target = parsed.hostname

    # Strip path component if it survived (rare, e.g. "github.com/foo")
    if "/" in target:
        target = target.split("/", 1)[0]

    # Strip port (skip if it's an IPv6 literal containing ':')
    if ":" in target and not _is_ip(target):
        target = target.rsplit(":", 1)[0]

    return original, target


def _expand_cidr(value: str) -> List[Target]:
    network = ipaddress.ip_network(value, strict=False)
    # `.hosts()` skips network/broadcast for IPv4 /<31; for /32 it yields the single host.
    return [
        Target(original=value, host=str(ip), ip=str(ip))
        for ip in network.hosts()
    ]


def _expand_range(value: str) -> List[Target]:
    start, end = value.split("-", 1)
    start_ip = ipaddress.IPv4Address(start.strip())
    end_ip = ipaddress.IPv4Address(end.strip())
    if int(end_ip) < int(start_ip):
        return []
    return [
        Target(
            original=value,
            host=str(ipaddress.IPv4Address(i)),
            ip=str(ipaddress.IPv4Address(i)),
        )
        for i in range(int(start_ip), int(end_ip) + 1)
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_line(line: str) -> List[Target]:
    """Parse a single input line into zero or more :class:`Target` records.

    DNS resolution is *not* performed here; domains come back with ``ip=None``.
    Use :func:`resolve_all` afterwards to batch-resolve them.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return []

    # CIDR (don't match URLs that contain '/')
    if "/" in line and "://" not in line:
        try:
            return _expand_cidr(line)
        except ValueError:
            pass  # fall through to other parsers

    # IPv4 range (must contain a dot to avoid matching e.g. "foo-bar")
    if "-" in line and "://" not in line and "." in line:
        try:
            return _expand_range(line)
        except (ValueError, ipaddress.AddressValueError):
            pass

    # URL / domain / single IP
    original, host = _normalize_url_or_domain(line)
    if not host:
        return []
    if _is_ip(host):
        return [Target(original=original, host=host, ip=host)]
    return [Target(original=original, host=host, ip=None)]


def load_targets(path: str) -> List[Target]:
    """Read a file and return all parsed targets (deduplicated, unresolved)."""
    seen = set()
    out: List[Target] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            for target in parse_line(line):
                key = (target.host, target.ip)
                if key in seen:
                    continue
                seen.add(key)
                out.append(target)
    return out


def resolve_all(targets: List[Target], workers: int = 50) -> List[Target]:
    """Resolve every domain-only target in parallel.

    Returns a *new* list; the input list is not mutated.
    """
    pending = [t for t in targets if t.ip is None and t.host]
    if not pending:
        return list(targets)

    unique_hosts = list({t.host for t in pending})
    with ThreadPoolExecutor(max_workers=min(workers, len(unique_hosts))) as pool:
        resolved = dict(zip(unique_hosts, pool.map(_resolve, unique_hosts)))

    out: List[Target] = []
    seen = set()
    for t in targets:
        ip = t.ip if t.ip is not None else resolved.get(t.host)
        new = Target(original=t.original, host=t.host, ip=ip)
        key = (new.host, new.ip)
        if key in seen:
            continue
        seen.add(key)
        out.append(new)
    return out
