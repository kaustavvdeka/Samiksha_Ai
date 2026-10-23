"""
security/permissions.py
=======================
Permission system that classifies every agent action into a risk tier.

Tiers:
  SAFE                → execute immediately, no prompt
  CONFIRMATION_REQUIRED → ask the user before executing
  BLOCKED             → refuse, never execute

Design:
  - The LLM NEVER executes shell commands directly.
  - All tool calls go through PermissionChecker.check() first.
  - The check is synchronous so it can be used in both sync and async contexts.

Usage:
    checker = PermissionChecker()
    level = checker.check("delete_file")
    if level == ActionLevel.SAFE:
        run_tool()
    elif level == ActionLevel.CONFIRMATION_REQUIRED:
        if checker.request_confirmation("delete_file", {"path": "..."}):
            run_tool()
    else:
        print("Action blocked.")
"""

from enum import Enum, auto

from config.settings import settings
from logger import get_logger

log = get_logger(__name__)


class ActionLevel(Enum):
    SAFE = auto()
    CONFIRMATION_REQUIRED = auto()
    BLOCKED = auto()


# --------------------------------------------------------------------------- #
# Static classification tables
# Anything not in these tables defaults to CONFIRMATION_REQUIRED (safe default)
# --------------------------------------------------------------------------- #

_SAFE_TOOLS: set[str] = {
    "open_application",
    "open_website",
    "search_google",
    "search_youtube",
    "open_url",
    "take_screenshot",
    "get_current_time",
    "get_system_info",
    "get_weather",
    "type_text",
    "press_key",
    "click",
    "move_mouse",
    "search_files",
    "open_file",
    "create_file",
    "read_file",
    "close_application",
    "list_running_applications",
    "focus_application",
    "hide_application",
    "restart_application",
    "send_whatsapp_message",
    "get_memory",
    "save_memory",
    "run_custom_workflow",
    "list_custom_workflows",
}



_BLOCKED_TOOLS: set[str] = {
    "execute_arbitrary_shell",   # Raw shell — never allowed
    "modify_registry",           # Windows registry
    "format_disk",               # Disk operations
    "rm_rf",                     # Destructive wildcard delete
}


class PermissionChecker:
    """
    Checks whether a tool is allowed to run and at what confirmation level.

    CONFIRMATION_REQUIRED tools are those listed in the .env variable
    CONFIRMATION_REQUIRED_TOOLS, plus any hardcoded below.
    """

    def __init__(self) -> None:
        # Tools that always require confirmation — from .env + hardcoded
        self._confirmation_tools: set[str] = set(
            settings.confirmation_required_tools
        ) | {
            "delete_file",
            "move_file",
            "rename_file",
            "shutdown_computer",
            "restart_computer",
            "execute_shell",
            "send_email",
            "send_message",
            "install_software",
            "modify_system_settings",
        }

    def check(self, tool_name: str) -> ActionLevel:
        """
        Classify a tool by its risk level.

        Args:
            tool_name: Name of the tool as registered in the tool registry.

        Returns:
            ActionLevel indicating whether to allow, confirm, or block.
        """
        if tool_name in _BLOCKED_TOOLS:
            log.warning("Blocked tool attempted", extra={"tool": tool_name})
            return ActionLevel.BLOCKED

        if tool_name in self._confirmation_tools:
            log.info(
                "Confirmation required for tool", extra={"tool": tool_name}
            )
            return ActionLevel.CONFIRMATION_REQUIRED

        if tool_name in _SAFE_TOOLS:
            return ActionLevel.SAFE

        # Unknown tool → require confirmation by default (fail-safe)
        log.warning(
            "Unknown tool — requiring confirmation", extra={"tool": tool_name}
        )
        return ActionLevel.CONFIRMATION_REQUIRED

    def request_confirmation(
        self, tool_name: str, arguments: dict
    ) -> bool:
        """
        Print a confirmation prompt and wait for the user's input.

        Args:
            tool_name: Tool being confirmed.
            arguments: Arguments that will be passed to the tool.

        Returns:
            True if the user confirmed, False otherwise.
        """
        print(
            f"\n⚠️  Samiksha needs your permission to: '{tool_name}'\n"
            f"   Arguments: {arguments}\n"
            f"   This action requires confirmation. Do you want me to continue? [y/N] ",
            end="",
            flush=True,
        )
        answer = input().strip().lower()
        confirmed = answer in ("y", "yes")
        log.info(
            "User confirmation",
            extra={"tool": tool_name, "confirmed": confirmed},
        )
        return confirmed

    def is_blocked(self, tool_name: str) -> bool:
        """Quick check — True if tool is in the blocked list."""
        return tool_name in _BLOCKED_TOOLS
