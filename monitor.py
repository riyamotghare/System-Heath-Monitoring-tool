"""monitor.py - system metrics (psutil) and network ping (subprocess).

No Streamlit code lives here, so these functions can be tested on their own.
"""

import ipaddress
import os
import platform
import re
import socket
import subprocess
import time

import psutil

# ---------------------------------------------------------------------------
# System information and metrics
# ---------------------------------------------------------------------------


def format_bytes(num_bytes):
    """Convert bytes to a readable string, e.g. 8589934592 -> '8.00 GB'."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024


def format_uptime(seconds):
    """Convert seconds to '2d 3h 15m' style text."""
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    return f"{days}d {hours}h {minutes}m"


def get_system_info():
    """Static-ish details: hostname, OS, CPU cores, uptime."""
    uptime_seconds = time.time() - psutil.boot_time()
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "cores_logical": psutil.cpu_count(logical=True),
        "cores_physical": psutil.cpu_count(logical=False),
        "uptime": format_uptime(uptime_seconds),
    }


def get_metrics():
    """Live resource usage for CPU, RAM and disk."""
    # interval=0.5 means psutil samples the CPU for half a second.
    # Without an interval the first call would always return 0.0.
    cpu_percent = psutil.cpu_percent(interval=0.5)

    ram = psutil.virtual_memory()

    # Root of the current drive: "C:\" on Windows, "/" on Linux/macOS.
    disk_path = os.path.abspath(os.sep)
    disk = psutil.disk_usage(disk_path)

    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram.percent,
        "ram_total": format_bytes(ram.total),
        "ram_available": format_bytes(ram.available),
        "disk_percent": disk.percent,
        "disk_total": format_bytes(disk.total),
        "disk_free": format_bytes(disk.free),
        "disk_path": disk_path,
    }


def check_thresholds(metrics, thresholds):
    """Return a list of warning messages for every resource over its limit."""
    warnings = []
    checks = [
        ("CPU", metrics["cpu_percent"], thresholds["cpu"]),
        ("RAM", metrics["ram_percent"], thresholds["ram"]),
        ("Disk", metrics["disk_percent"], thresholds["disk"]),
    ]
    for name, value, limit in checks:
        if value > limit:
            warnings.append(
                f"{name} usage is {value:.1f}%, above the {limit}% threshold."
            )
    return warnings


# ---------------------------------------------------------------------------
# Network connectivity (ping)
# ---------------------------------------------------------------------------

# Letters, digits, dots and hyphens; each label 1-63 chars, no leading/trailing hyphen.
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)


def validate_host(host):
    """Return (is_valid, cleaned_host_or_error_message).

    Only accepts a valid IP address or hostname. This blocks empty input,
    spaces, and characters like ; | & which are used in command injection.
    """
    host = (host or "").strip()
    if not host:
        return False, "Please enter a hostname or IP address."
    try:
        ipaddress.ip_address(host)
        return True, host
    except ValueError:
        pass
    if _HOSTNAME_RE.match(host):
        return True, host
    return False, "Invalid hostname or IP address. Use letters, digits, dots and hyphens only."


def build_ping_command(host, count=4, per_reply_timeout=2):
    """Build the OS-specific ping command as a list (never a single string)."""
    system = platform.system().lower()
    if system == "windows":
        # -n = number of echo requests, -w = timeout per reply in milliseconds
        return ["ping", "-n", str(count), "-w", str(per_reply_timeout * 1000), host]
    if system == "darwin":
        # macOS: -c = count, -W = wait per reply in milliseconds
        return ["ping", "-c", str(count), "-W", str(per_reply_timeout * 1000), host]
    # Linux: -c = count, -W = wait per reply in seconds
    return ["ping", "-c", str(count), "-W", str(per_reply_timeout), host]


def ping_host(host, count=4, per_reply_timeout=2):
    """Ping a host and return a result dictionary.

    Keys: success (bool), output (str), error (str or None).
    """
    valid, result = validate_host(host)
    if not valid:
        return {"success": False, "output": "", "error": result}
    host = result

    command = build_ping_command(host, count, per_reply_timeout)
    # Overall safety limit so the app can never hang forever.
    overall_timeout = count * (per_reply_timeout + 1) + 5

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=overall_timeout,
            shell=False,  # explicit: arguments are passed as a list, not through a shell
        )
    except FileNotFoundError:
        return {
            "success": False,
            "output": "",
            "error": "The 'ping' command was not found on this system.",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Ping timed out after {overall_timeout} seconds.",
        }
    except OSError as exc:
        return {"success": False, "output": "", "error": f"Could not run ping: {exc}"}

    output = (completed.stdout or "") + (completed.stderr or "")
    success = completed.returncode == 0

    # Windows can return exit code 0 even for "Destination host unreachable",
    # so also require an actual reply (which always contains "TTL=").
    if platform.system().lower() == "windows":
        success = success and "TTL=" in output.upper()

    return {"success": success, "output": output.strip(), "error": None}
