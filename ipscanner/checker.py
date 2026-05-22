"""Reachability checkers — ICMP ping, TCP connect, HTTP HEAD.

Platform notes
--------------
* Windows  — ping -n 1 -w <ms>
* Linux / macOS — ping -c 1 -W <s>
* Android / Termux (no root) — ICMP blocked; TCP and HTTP work fine.
* Android / Termux (rooted)  — ICMP works if the process runs as root.
  The scanner detects root via ``su -c id`` and re-launches itself
  under ``su`` automatically when the user picks ICMP.
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .parser import Target

_IS_WINDOWS = platform.system().lower() == "windows"

IS_ANDROID: bool = (
    "com.termux" in os.environ.get("PREFIX", "")
    or os.path.exists("/system/build.prop")
)

# True when this process is already running as root (UID 0).
IS_ROOT: bool = (os.getuid() == 0) if hasattr(os, "getuid") else True


def has_su() -> bool:
    """Return True if the ``su`` binary is available and grants root access."""
    try:
        result = subprocess.run(
            ["su", "-c", "id"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0 and b"uid=0" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def relaunch_as_root() -> None:
    """Re-exec the current process under ``su -c ...`` and exit.

    Called only on Android when the user wants ICMP and root is available.
    The child process inherits all arguments so the scan continues normally.
    """
    cmd = ["su", "-c", " ".join([sys.executable] + sys.argv)]
    os.execv("/system/xbin/su", cmd) if os.path.exists("/system/xbin/su") \
        else os.execvp("su", cmd)


@dataclass
class CheckResult:
    target: Target
    alive: bool
    latency_ms: Optional[float]
    method: str
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# ICMP
# ---------------------------------------------------------------------------

def _ping_command(host: str, timeout_ms: int) -> list[str]:
    if _IS_WINDOWS:
        return ["ping", "-n", "1", "-w", str(timeout_ms), host]
    timeout_s = max(1, round(timeout_ms / 1000))
    return ["ping", "-c", "1", "-W", str(timeout_s), host]


def icmp_check(target: Target, timeout_ms: int = 1000) -> CheckResult:
    host = target.ip or target.host
    if not host:
        return CheckResult(target, False, None, "icmp", "no host")

    # On Android without root, ICMP is always blocked.
    # relaunch_as_root() should have been called before we get here,
    # but guard anyway so results are never silently wrong.
    if IS_ANDROID and not IS_ROOT:
        return CheckResult(
            target, False, None, "icmp",
            "ICMP requires root — run with su or choose tcp/http",
        )

    start = time.perf_counter()
    try:
        result = subprocess.run(
            _ping_command(host, timeout_ms),
            capture_output=True,
            timeout=(timeout_ms / 1000) + 2,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(target, False, None, "icmp", "timeout")
    except FileNotFoundError:
        return CheckResult(target, False, None, "icmp", "ping binary not found")
    except OSError as e:
        return CheckResult(target, False, None, "icmp", str(e))

    latency = (time.perf_counter() - start) * 1000
    alive = result.returncode == 0
    return CheckResult(target, alive, latency if alive else None, "icmp")


# ---------------------------------------------------------------------------
# TCP
# ---------------------------------------------------------------------------

def tcp_check(target: Target, port: int = 443, timeout_s: float = 2.0) -> CheckResult:
    host = target.ip or target.host
    if not host:
        return CheckResult(target, False, None, f"tcp:{port}", "no host")

    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(target, True, latency, f"tcp:{port}")
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return CheckResult(target, False, None, f"tcp:{port}", type(e).__name__)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

_USER_AGENT = "Penhandev-IP-Scanner/3.0 (+https://github.com/penhandev/IP-Scanner)"


def http_check(
    target: Target,
    timeout_s: float = 3.0,
    scheme: str = "https",
) -> CheckResult:
    host = target.host
    if not host:
        return CheckResult(target, False, None, "http", "no host")

    url = f"{scheme}://{host}/"
    start = time.perf_counter()
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": _USER_AGENT})
        with urlopen(req, timeout=timeout_s) as resp:
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(target, resp.status < 500, latency, "http")
    except HTTPError as e:
        latency = (time.perf_counter() - start) * 1000
        return CheckResult(target, e.code < 500, latency, "http", f"HTTP {e.code}")
    except URLError as e:
        return CheckResult(target, False, None, "http", str(getattr(e, "reason", e)))
    except (socket.timeout, OSError) as e:
        return CheckResult(target, False, None, "http", type(e).__name__)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_CHECKERS = {
    "icmp": icmp_check,
    "tcp": tcp_check,
    "http": http_check,
}


def check(target: Target, method: str = "icmp", **kwargs) -> CheckResult:
    fn = _CHECKERS.get(method)
    if fn is None:
        return CheckResult(target, False, None, method, "unknown method")
    return fn(target, **kwargs)