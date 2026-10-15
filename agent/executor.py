"""
agent/executor.py
=================
Tool executor: the layer between the LLM's decisions and actual tool calls.

Responsibilities:
  1. Receive a list of ToolCall objects from the planner.
  2. Check each tool's permission level.
  3. Execute permitted tools via the registry.
  4. Return results as strings.

Security guarantee:
  No tool is ever called without passing through PermissionChecker first.
"""

from llm.base import ToolCall
from security.permissions import PermissionChecker, ActionLevel
from tools.registry import execute_tool, has_tool
from logger import get_logger

log = get_logger(__name__)


class Executor:
    """
    Executes tool calls after security validation.

    Design:
      - execute_plan()  → execute a list of ToolCall objects in order
      - execute_one()   → execute a single ToolCall
    """

    def __init__(self) -> None:
        self.permission_checker = PermissionChecker()

    def execute_plan(self, tool_calls: list[ToolCall]) -> list[tuple[str, str]]:
        """
        Execute a list of tool calls in order.

        Args:
            tool_calls: Ordered list of ToolCall objects from the LLM planner.

        Returns:
            List of (tool_name, result) tuples.
        """
        results: list[tuple[str, str]] = []
        for call in tool_calls:
            name, result = self.execute_one(call)
            results.append((name, result))
        return results

    def execute_one(self, call: ToolCall) -> tuple[str, str]:
        """
        Execute a single tool call with permission checking.

        Args:
            call: ToolCall containing tool_name and arguments.

        Returns:
            Tuple of (tool_name, result_string).
        """
        tool_name = call.tool_name
        arguments = call.arguments

        log.info(
            "Executor received tool call",
            extra={"tool": tool_name, "tool_args": arguments},
        )

        # 1. Check the tool exists
        if not has_tool(tool_name):
            result = (
                f"I don't know how to use the tool '{tool_name}'. "
                "It may not be registered yet."
            )
            log.warning("Unknown tool called", extra={"tool": tool_name})
            return tool_name, result

        # 2. Check permissions
        level = self.permission_checker.check(tool_name)

        if level == ActionLevel.BLOCKED:
            result = (
                f"The action '{tool_name}' is blocked for safety reasons. "
                "I cannot perform this action."
            )
            log.warning("Blocked tool call", extra={"tool": tool_name})
            return tool_name, result

        if level == ActionLevel.CONFIRMATION_REQUIRED:
            confirmed = self.permission_checker.request_confirmation(
                tool_name, arguments
            )
            if not confirmed:
                result = f"Action '{tool_name}' was cancelled at your request."
                return tool_name, result

        # 3. Execute
        try:
            result = execute_tool(tool_name, arguments)
        except Exception as exc:
            result = f"Tool '{tool_name}' failed: {exc}"
            log.error(
                "Tool execution error",
                extra={"tool": tool_name, "error": str(exc)},
            )

        return tool_name, result
