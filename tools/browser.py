"""
tools/browser.py
================
Browser automation tools using Playwright.

Design:
  - Uses Playwright (async API wrapped in sync for simplicity).
  - Opens the system's default browser OR Brave specifically if requested.
  - Does NOT use coordinate-based clicking — uses proper selectors.

Milestone 4 tools implemented here:
  open_website    — navigate to a URL
  open_url        — alias for open_website
  search_google   — open google.com and search
  search_youtube  — open youtube.com and search

Prerequisites:
    pip install playwright
    playwright install chromium   (or use system browsers)
"""

import asyncio
import subprocess
import platform
from typing import Optional

from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)

_OS = platform.system()


# --------------------------------------------------------------------------- #
# Simple URL-based tools (no Playwright needed — just opens URLs)
# For Milestone 3 these open in the default browser via subprocess/webbrowser.
# --------------------------------------------------------------------------- #

def _open_url_in_browser(url: str, browser_name: Optional[str] = None) -> bool:
    """
    Open a URL in the system's default browser or a named browser.

    Args:
        url:          The URL to open.
        browser_name: Optional browser name (e.g. "Brave", "Chrome").

    Returns:
        True on success, False on failure.
    """
    import webbrowser

    if browser_name:
        # Try to open in a specific browser
        key = browser_name.lower()
        try:
            if _OS == "Darwin":
                app_map = {
                    "brave": "Brave Browser",
                    "chrome": "Google Chrome",
                    "firefox": "Firefox",
                    "safari": "Safari",
                    "edge": "Microsoft Edge",
                }
                app = app_map.get(key, browser_name)
                subprocess.Popen(
                    ["open", "-a", app, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            elif _OS == "Linux":
                cmd_map = {
                    "brave": "brave-browser",
                    "chrome": "google-chrome",
                    "firefox": "firefox",
                }
                cmd = cmd_map.get(key, key)
                subprocess.Popen(
                    [cmd, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            elif _OS == "Windows":
                cmd_map = {
                    "brave": "brave",
                    "chrome": "chrome",
                    "firefox": "firefox",
                    "edge": "msedge",
                }
                cmd = cmd_map.get(key, key)
                subprocess.Popen(
                    [cmd, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
        except Exception as exc:
            log.warning(
                "Specific browser failed, falling back to default",
                extra={"browser": browser_name, "error": str(exc)},
            )

    # Default browser fallback
    webbrowser.open(url)
    return True


# --------------------------------------------------------------------------- #
# Registered tools
# --------------------------------------------------------------------------- #

@register_tool(description="Open a website URL in the browser.")
def open_website(url: str) -> str:
    """
    Open a URL in the default web browser.

    Args:
        url: The full URL to open (e.g. https://youtube.com).

    Returns:
        Confirmation message.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    log.info("Opening website", extra={"url": url})
    success = _open_url_in_browser(url)
    return f"Opening {url}." if success else f"Failed to open {url}."


@register_tool(description="Open a URL — alias for open_website.")
def open_url(url: str) -> str:
    """
    Open a URL in the default web browser.

    Args:
        url: The URL to navigate to.

    Returns:
        Confirmation message.
    """
    return open_website(url)


@register_tool(description="Search Google for a query and open results in the browser.")
def search_google(query: str) -> str:
    """
    Open a Google search for the given query in the default browser.

    Args:
        query: The search query string.

    Returns:
        Confirmation message.
    """
    import urllib.parse
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    log.info("Google search", extra={"query": query})
    _open_url_in_browser(url)
    return f"Searching Google for '{query}'."


@register_tool(description="Search YouTube for a query and open results in the browser.")
def search_youtube(query: str) -> str:
    """
    Open a YouTube search for the given query in the default browser.

    Args:
        query: The search query string.

    Returns:
        Confirmation message.
    """
    import urllib.parse
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    log.info("YouTube search", extra={"query": query})
    _open_url_in_browser(url)
    return f"Searching YouTube for '{query}'."


@register_tool(
    description="Open a website in a specific browser (e.g. Brave, Chrome)."
)
def open_website_in_browser(url: str, browser: str) -> str:
    """
    Open a URL in a specific named browser.

    Args:
        url:     The full URL to open.
        browser: Browser name (e.g. "Brave", "Chrome", "Firefox").

    Returns:
        Confirmation message.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    log.info("Opening in specific browser", extra={"url": url, "browser": browser})
    success = _open_url_in_browser(url, browser_name=browser)
    if success:
        return f"Opening {url} in {browser}."
    return f"Could not open {url} in {browser}."


@register_tool(
    description="Open YouTube website in the browser."
)
def open_youtube() -> str:
    """
    Open YouTube in the default browser.

    Returns:
        Confirmation message.
    """
    return open_website("https://www.youtube.com")
