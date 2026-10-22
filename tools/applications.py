"""
tools/applications.py
=====================
Comprehensive tools for launching, closing, switching, and managing desktop applications.

Capabilities:
  - Dynamic discovery & fuzzy matching of installed apps on macOS/Linux/Windows
  - Non-blocking launching (open_application)
  - Graceful closing + process termination fallback (close_application)
  - Window focus / app switching (focus_application)
  - Window hiding / minimizing (hide_application)
  - Listing active user-facing applications (list_running_applications)
  - Restarting applications (restart_application)
"""

import difflib
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)

_OS = platform.system()  # "Darwin" | "Linux" | "Windows"

# ------------------------------------------------------------------ #
# Static common aliases mapping (fast lookup)
# ------------------------------------------------------------------ #

_APP_MAP_MACOS: dict[str, str] = {
    "brave": "Brave Browser",
    "brave browser": "Brave Browser",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "edge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "cursor": "Cursor",
    "pycharm": "PyCharm",
    "xcode": "Xcode",
    "sublime": "Sublime Text",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "iterm2": "iTerm",
    "finder": "Finder",
    "whatsapp": "WhatsApp",
    "slack": "Slack",
    "discord": "Discord",
    "telegram": "Telegram",
    "spotify": "Spotify",
    "zoom": "zoom.us",
    "notion": "Notion",
    "obsidian": "Obsidian",
    "figma": "Figma",
    "notes": "Notes",
    "calendar": "Calendar",
    "mail": "Mail",
    "messages": "Messages",
    "facetime": "FaceTime",
    "photos": "Photos",
    "preview": "Preview",
    "calculator": "Calculator",
    "system preferences": "System Preferences",
    "system settings": "System Settings",
    "activity monitor": "Activity Monitor",
    "textedit": "TextEdit",
    "vlc": "VLC",
    "chatgpt": "ChatGPT",
    "docker": "Docker",
    "postman": "Postman",
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
    "terminal": "wt",  # Windows Terminal
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


def _discover_macos_installed_apps() -> dict[str, str]:
    """
    Dynamically scan macOS application directories for installed .app bundles.
    Returns a dict mapping lowercased app name to its clean display name.
    """
    search_dirs = [
        Path("/Applications"),
        Path("/System/Applications"),
        Path("/System/Applications/Utilities"),
        Path.home() / "Applications",
    ]
    apps: dict[str, str] = {}
    for directory in search_dirs:
        if directory.exists():
            for app_path in directory.glob("*.app"):
                name = app_path.stem
                apps[name.lower()] = name
    return apps


def _resolve_application_name(requested: str) -> str:
    """
    Resolve a user's spoken or typed app name to the exact system application name
    using static alias mappings, installed app scanning, and fuzzy string matching.
    """
    clean = requested.strip()
    key = clean.lower()

    # 1. Direct match in static alias map
    app_map = _get_app_map()
    if key in app_map:
        return app_map[key]

    # 2. On macOS, dynamically scan installed apps
    if _OS == "Darwin":
        installed = _discover_macos_installed_apps()
        if key in installed:
            return installed[key]

        # 3. Substring matching (e.g. "brave" in "brave browser", "monitor" in "activity monitor")
        for app_key, app_name in installed.items():
            if key in app_key or app_key in key:
                return app_name

        # 4. Fuzzy matching (handles minor spelling discrepancies)
        close = difflib.get_close_matches(key, list(installed.keys()), n=1, cutoff=0.5)
        if close:
            return installed[close[0]]

    # Fallback to the raw requested name
    return clean


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


# --------------------------------------------------------------------------- #
# Public Tools
# --------------------------------------------------------------------------- #

@register_tool(description="Open a desktop application by name.")
def open_application(application: str) -> str:
    """
    Open a desktop application by name.

    Args:
        application: The name of the application to open (e.g. "VS Code", "Brave", "WhatsApp").

    Returns:
        A message indicating success or failure.
    """
    mapped = _resolve_application_name(application)

    log.info(
        "Opening application",
        extra={"requested": application, "mapped": mapped, "os": _OS},
    )

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
    Close or quit a running desktop application by name.

    Args:
        application: The application name to close (e.g. "Brave", "Spotify", "VS Code").

    Returns:
        Status message confirming the application was closed.
    """
    mapped = _resolve_application_name(application)
    key = mapped.strip().lower()
    log.info("Closing application", extra={"application": application, "mapped": mapped})

    # 1. On macOS, first attempt graceful AppleScript quit so the app can save state
    if _OS == "Darwin":
        try:
            script = f'tell application "{mapped}" to quit'
            res = subprocess.run(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            if res.returncode == 0:
                return f"Closed {application}."
        except Exception:
            pass  # Fall through to process termination

    # 2. Terminate matching process using psutil
    try:
        import psutil
        killed: list[str] = []
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                proc_name = (proc.info["name"] or "").lower()
                if key in proc_name or proc_name in key:
                    proc.terminate()
                    killed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            return f"Closed {', '.join(set(killed))}."
        else:
            return f"No running process found matching '{application}'."
    except ImportError:
        return "psutil is not installed — cannot close applications programmatically."
    except Exception as exc:
        return f"Failed to close {application}: {exc}"


@register_tool(description="List all currently open desktop applications.")
def list_running_applications() -> str:
    """
    List currently running desktop applications on the computer.

    Returns:
        A list of active applications.
    """
    log.info("Listing running applications")

    # 1. macOS native GUI process listing via AppleScript
    if _OS == "Darwin":
        try:
            cmd = (
                'osascript -e \'tell application "System Events" '
                'to get name of every process whose background only is false\''
            )
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                apps = [a.strip() for a in res.stdout.strip().split(",") if a.strip()]
                return f"Currently running applications ({len(apps)}): {', '.join(apps)}."
        except Exception as exc:
            log.warning("AppleScript process list failed", extra={"error": str(exc)})

    # 2. Cross-platform fallback via psutil
    try:
        import psutil
        common_gui_names = {
            "brave", "chrome", "firefox", "safari", "code", "cursor", "sublime",
            "terminal", "iterm", "whatsapp", "slack", "discord", "spotify",
            "notion", "obsidian", "figma", "vlc", "notes", "calendar", "mail"
        }
        running: set[str] = set()
        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info["name"] or "").lower()
                for gui in common_gui_names:
                    if gui in pname:
                        running.add(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if running:
            return f"Currently open applications: {', '.join(sorted(running))}."
        return "No common desktop applications detected running."
    except ImportError:
        return "Could not inspect running applications (psutil not available)."
    except Exception as exc:
        return f"Error listing applications: {exc}"


@register_tool(description="Bring a running application window to the foreground.")
def focus_application(application: str) -> str:
    """
    Bring a running application to focus (switch to it).

    Args:
        application: Name of the application to switch to (e.g. "Brave", "VS Code").

    Returns:
        Confirmation message.
    """
    mapped = _resolve_application_name(application)
    log.info("Focusing application", extra={"application": application, "mapped": mapped})

    if _OS == "Darwin":
        try:
            script = f'tell application "{mapped}" to activate'
            res = subprocess.run(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=4,
            )
            if res.returncode == 0:
                return f"Switched to {application}."
            return f"Could not bring {application} to focus. Make sure it is running."
        except Exception as exc:
            return f"Failed to switch to {application}: {exc}"

    # For Linux / Windows fallback: launch or re-open brings it to focus
    return open_application(application)


@register_tool(description="Hide or minimize a running application window.")
def hide_application(application: str) -> str:
    """
    Hide or minimize an application's windows.

    Args:
        application: Name of the application to hide (e.g. "Spotify", "Brave").

    Returns:
        Confirmation message.
    """
    mapped = _resolve_application_name(application)
    log.info("Hiding application", extra={"application": application, "mapped": mapped})

    if _OS == "Darwin":
        try:
            script = f'tell application "System Events" to set visible of process "{mapped}" to false'
            res = subprocess.run(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=4,
            )
            if res.returncode == 0:
                return f"Minimized {application}."
            return f"Could not minimize {application}. Make sure it is currently active."
        except Exception as exc:
            return f"Failed to minimize {application}: {exc}"

    return f"Minimizing applications is not supported on {_OS}."


@register_tool(description="Restart a desktop application by closing and reopening it.")
def restart_application(application: str) -> str:
    """
    Restart a desktop application (closes it and launches it again).

    Args:
        application: Name of the application to restart (e.g. "Brave", "VS Code").

    Returns:
        Confirmation message.
    """
    log.info("Restarting application", extra={"application": application})
    close_res = close_application(application)
    time.sleep(1.0)
    open_res = open_application(application)
    return f"Restarting {application}: {close_res} {open_res}"
