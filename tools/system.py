"""
tools/system.py
===============
System information and utility tools.
"""

import datetime
import platform

from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)


@register_tool(description="Get the current date and time.")
def get_current_time() -> str:
    """
    Get the current local date and time.

    Returns:
        Human-readable current date and time string.
    """
    now = datetime.datetime.now()
    return now.strftime("It is %A, %B %d, %Y at %I:%M %p.")


@register_tool(description="Get basic system information.")
def get_system_info() -> str:
    """
    Get the current system's OS, CPU, and memory information.

    Returns:
        Multi-line string with system details.
    """
    import psutil

    uname = platform.uname()
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=0.5)

    return (
        f"OS: {uname.system} {uname.release}\n"
        f"Machine: {uname.machine}\n"
        f"CPU Usage: {cpu_pct}%\n"
        f"Memory: {mem.used // (1024**2)} MB used / "
        f"{mem.total // (1024**2)} MB total "
        f"({mem.percent}% used)"
    )
