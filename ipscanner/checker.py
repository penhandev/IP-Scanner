"""Reachability checkers — ICMP ping, TCP connect, HTTP HEAD.

Platform notes
--------------
* Windows  — ping -n 1 -w <ms>
* Linux / macOS — unprivileged SOCK_DGRAM/ICMP first, falls back to ping
* Android / Termux (no root) — unprivileged SOCK_DGRAM/ICMP works on most
  modern devices (kernel's ping_group_range is usually wide open). If the
  kernel rejects it, we fall back to the ``ping`` subprocess, and finally
  to a root re-launch via ``su``.
* Android / Termux (rooted)  — both paths work; subprocess ping is used.
"""

from __future__ import annotations

import os
import platform
import select
import socket
import struct
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


def _icmp_checksum(data: bytes) -> int:
    s = 0
    for i in range(0, len(data) - 1, 2):
        s += (data[i] << 8) | data[i + 1]
    if len(data) % 2:
        s += data[-1] << 8
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF


def unprivileged_icmp_supported() -> bool:
    """Return True if the kernel/GID allows SOCK_DGRAM/ICMP without root."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
    except (PermissionError, OSError):
        return False
    s.close()
    return True


_UNAVAILABLE = object()  # sentinel returned when the kernel rejects SOCK_DGRAM/ICMP


def _icmp_socket_ping(host: str, timeout_ms: int):
    """Send one ICMP Echo via SOCK_DGRAM (no root needed on permissive kernels).

    Returns one of:
        ``_UNAVAILABLE``                  socket could not be opened — caller
                                          should try the subprocess fallback
        ``(True,  latency_ms, None)``     reply received
        ``(False, None, error_string)``   reachable kernel, but no reply
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
    except (PermissionError, OSError):
        return _UNAVAILABLE

    try:
        try:
            addr = socket.gethostbyname(host)
        except OSError as e:
            return (False, None, f"resolve: {e}")

        ident = os.getpid() & 0xFFFF
        seq = 1
        header = struct.pack("!BBHHH", 8, 0, 0, ident, seq)
        payload = b"penhandev-ipscanner"
        chksum = _icmp_checksum(header + payload)
        packet = struct.pack("!BBHHH", 8, 0, chksum, ident, seq) + payload

        start = time.perf_counter()
        try:
            sock.sendto(packet, (addr, 0))
        except OSError as e:
            return (False, None, f"send: {e}")

        # select() is more portable than settimeout() for one-shot ICMP
        ready, _, _ = select.select([sock], [], [], timeout_ms / 1000)
        if not ready:
            return (False, None, "timeout")

        try:
            data, _ = sock.recvfrom(1024)
        except OSError as e:
            return (False, None, f"recv: {e}")

        latency = (time.perf_counter() - start) * 1000

        # SOCK_DGRAM/ICMP delivers only the ICMP message (no IP header).
        # Validate type=0 (Echo Reply) — kernel filters by ident for us.
        if len(data) >= 1 and data[0] == 0:
            return (True, latency, None)
        return (False, None, "no reply")
    finally:
        sock.close()


def icmp_check(target: Target, timeout_ms: int = 1000) -> CheckResult:
    host = target.ip or target.host
    if not host:
        return CheckResult(target, False, None, "icmp", "no host")

    # Prefer unprivileged SOCK_DGRAM/ICMP on Linux/Android when not root.
    # Works on most modern Android (ping_group_range is usually 0..MAX).
    if not _IS_WINDOWS and not IS_ROOT:
        res = _icmp_socket_ping(host, timeout_ms)
        if res is not _UNAVAILABLE:
            alive, latency, err = res
            return CheckResult(target, alive, latency, "icmp", err)
        # Kernel/GID rejected it. On non-root Android the ping binary also
        # needs root, so don't bother with the subprocess fallback there.
        if IS_ANDROID:
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