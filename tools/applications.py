"""
tools/applications.py
=====================
Tools for launching and closing desktop applications.

Design:
  - Uses subprocess.Popen (non-blocking) so the agent doesn't freeze.
  - Platform-aware: macOS / Linux / Windows handled explicitly.
  - Returns a human-readable status string (not raises) so the agent
    can relay the message to TTS naturally.

Usage:
    from tools.applications import open_application
    result = open_application("VS Code")
    # → "Opening VS Code." or "I couldn't find VS Code on this computer."
"""

import platform
import subprocess
from typing import Optional

from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)

_OS = platform.system()  # "Darwin" | "Linux" | "Windows"

# ------------------------------------------------------------------ #
# Application name → system command mapping
# macOS uses 'open -a', Linux uses direct command, Windows uses 'start'
# ------------------------------------------------------------------ #

_APP_MAP_MACOS: dict[str, str] = {
    "brave": "Brave Browser",
    "brave browser": "Brave Browser",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "iterm2": "iTerm",
    "finder": "Finder",
    "whatsapp": "WhatsApp",
    "slack": "Slack",
    "discord": "Discord",
    "spotify": "Spotify",
    "zoom": "zoom.us",
    "notion": "Notion",
    "obsidian": "Obsidian",
    "figma": "Figma",
    "xcode": "Xcode",
    "pycharm": "PyCharm",
    "cursor": "Cursor",
    "notes": "Notes",
    "calendar": "Calendar",
    "mail": "Mail",
    "messages": "Messages",
    "facetime": "FaceTime",
    "photos": "Photos",
    "preview": "Preview",
    "calculator": "Calculator",
    "system preferences": "System Preferences",
    "system settings": "System Preferences",
    "activity monitor": "Activity Monitor",
    "textedit": "TextEdit",
    "vlc": "VLC",
}

_APP_MAP_LINUX: dict[str, str] = {
    "brave": "brave-browser",
    "brave browser": "brave-browser",
    "chrome": "google-chrome",
    "google chrome": "google-chrome",
    "firefox": "firefox",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "terminal": "gnome-terminal",
    "file manager": "nautilus",
    "whatsapp": "whatsapp-desktop",
    "slack": "slack",
    "discord": "discord",
    "spotify": "spotify",
    "zoom": "zoom",
    "vlc": "vlc",
    "gedit": "gedit",
    "calculator": "gnome-calculator",
}

_APP_MAP_WINDOWS: dict[str, str] = {
    "brave": "brave",
    "brave browser": "brave",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "terminal": "wt",          # Windows Terminal
    "notepad": "notepad",
    "calculator": "calc",
    "explorer": "explorer",
    "file manager": "explorer",
    "whatsapp": "WhatsApp",
    "slack": "slack",
    "discord": "discord",
    "spotify": "spotify",
    "zoom": "zoom",
    "vlc": "vlc",
    "task manager": "taskmgr",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
}


def _get_app_map() -> dict[str, str]:
    """Return the platform-appropriate application map."""
    if _OS == "Darwin":
        return _APP_MAP_MACOS
    elif _OS == "Linux":
        return _APP_MAP_LINUX
    elif _OS == "Windows":
        return _APP_MAP_WINDOWS
    return {}


def _launch_macos(app_name: str) -> bool:
    """Launch an app on macOS using 'open -a'. Returns True on success."""
    try:
        res = subprocess.run(
            ["open", "-a", app_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        return res.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def _launch_linux(command: str) -> bool:
    """Launch an app on Linux by command name. Returns True on success."""
    import shutil
    cmd = command.split()[0]
    if not shutil.which(cmd):
        return False
    try:
        subprocess.Popen(
            command.split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False


def _launch_windows(app: str) -> bool:
    """Launch an app on Windows using 'start'. Returns True on success."""
    try:
        subprocess.Popen(
            ["start", "", app],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


@register_tool(description="Open a desktop application by name.")
def open_application(application: str) -> str:
    """
    Open a desktop application by name.

    Args:
        application: The name of the application to open (e.g. "VS Code", "Brave", "WhatsApp").

    Returns:
        A message indicating success or failure.
    """
    key = application.strip().lower()
    app_map = _get_app_map()
    mapped = app_map.get(key)

    log.info(
        "Opening application",
        extra={"requested": application, "mapped": mapped, "os": _OS},
    )

    if not mapped:
        # Try the raw name as a fallback
        mapped = application

    success = False
    if _OS == "Darwin":
        success = _launch_macos(mapped)
    elif _OS == "Linux":
        success = _launch_linux(mapped)
    elif _OS == "Windows":
        success = _launch_windows(mapped)

    if success:
        return f"Opening {application}."
    else:
        return (
            f"I couldn't find {application} on this computer. "
            "Make sure it is installed."
        )


@register_tool(description="Close a running desktop application by name.")
def close_application(application: str) -> str:
    """
    Close (kill) a running application by process name.

    Args:
        application: The application name to close (e.g. "Brave", "Spotify").

    Returns:
        Status message.
    """
    key = application.strip().lower()
    log.info("Closing application", extra={"application": application})

    try:
        import psutil
        killed = []
        for proc in psutil.process_iter(["name", "pid"]):
            proc_name = (proc.info["name"] or "").lower()
            if key in proc_name or proc_name in key:
                proc.terminate()
                killed.append(proc.info["name"])

        if killed:
            return f"Closed {', '.join(set(killed))}."
        else:
            return f"No running process found matching '{application}'."
    except ImportError:
        return "psutil is not installed — cannot close applications programmatically."
    except Exception as exc:
        return f"Failed to close {application}: {exc}"
