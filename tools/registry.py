"""
tools/registry.py
=================
Central tool registry for the Samiksha agent.

Design:
  Tools are ordinary Python functions decorated with @register_tool.
  The registry stores:
    - The callable
    - A JSON Schema description (for passing to the LLM)
    - Metadata (name, description)

  The agent planner calls get_tool_schemas() to pass to the LLM.
  The executor calls execute(tool_name, arguments) to actually run a tool.

Adding a new tool:
  1. Write the function in the appropriate tools/*.py file.
  2. Apply the @register_tool decorator.
  3. Import the module in tools/__init__.py.
  The registry picks it up automatically — no manual registration needed.

Usage:
    from tools.registry import register_tool, execute_tool, get_tool_schemas

    @register_tool(description="Open an application by name")
    def open_application(application: str) -> str:
        ...
"""

import functools
import inspect
from typing import Any, Callable

from logger import get_logger

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Internal storage
# --------------------------------------------------------------------------- #

_REGISTRY: dict[str, dict[str, Any]] = {}
# Shape: { tool_name: { "fn": callable, "schema": dict, "description": str } }


# --------------------------------------------------------------------------- #
# Decorator
# --------------------------------------------------------------------------- #

def register_tool(
    fn: Callable | None = None,
    *,
    description: str = "",
    name: str | None = None,
) -> Callable:
    """
    Decorator that registers a function as an agent tool.

    Can be used with or without arguments:
        @register_tool
        def my_tool(...): ...

        @register_tool(description="Does X", name="my_tool")
        def my_tool(...): ...

    Args:
        fn:          The function to register (when used without arguments).
        description: Human-readable description of what the tool does.
        name:        Override the tool name (defaults to the function name).

    Returns:
        The original function, unchanged (decorator is transparent).
    """

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or (inspect.getdoc(func) or "").split("\n")[0]
        schema = _build_schema(func, tool_name, tool_desc)

        _REGISTRY[tool_name] = {
            "fn": func,
            "schema": schema,
            "description": tool_desc,
        }
        log.debug("Tool registered", extra={"tool": tool_name})

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    if fn is not None:
        # Called as @register_tool (no parentheses)
        return decorator(fn)
    # Called as @register_tool(...)
    return decorator


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def get_tool_schemas() -> list[dict[str, Any]]:
    """
    Return all registered tools in OpenAI function-calling format.

    The LLM uses this list to decide which tools to invoke.
    """
    return [entry["schema"] for entry in _REGISTRY.values()]


def get_tool_names() -> list[str]:
    """Return a list of all registered tool names."""
    return list(_REGISTRY.keys())


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """
    Execute a registered tool by name with the given arguments.

    Args:
        tool_name: Must be in the registry.
        arguments: Dict matching the tool's parameter names.

    Returns:
        String result from the tool (all tools must return str).

    Raises:
        KeyError:  If the tool is not registered.
        TypeError: If arguments don't match the function signature.
        Exception: Any exception raised by the tool itself.
    """
    if tool_name not in _REGISTRY:
        raise KeyError(
            f"Tool '{tool_name}' is not registered. "
            f"Available tools: {list(_REGISTRY.keys())}"
        )

    fn = _REGISTRY[tool_name]["fn"]
    log.info(
        "Executing tool",
        extra={"tool": tool_name, "tool_args": arguments},
    )

    try:
        result = fn(**arguments)
        log.info(
            "Tool completed",
            extra={"tool": tool_name, "result_preview": str(result)[:100]},
        )
        return str(result)
    except TypeError as exc:
        raise TypeError(
            f"Invalid arguments for tool '{tool_name}': {exc}"
        ) from exc


def has_tool(tool_name: str) -> bool:
    """Check if a tool exists in the registry."""
    return tool_name in _REGISTRY


# --------------------------------------------------------------------------- #
# Schema builder
# --------------------------------------------------------------------------- #

def _build_schema(fn: Callable, tool_name: str, description: str) -> dict:
    """
    Build an OpenAI-compatible function schema from a Python function's
    type annotations and docstring.

    Only supports str, int, float, bool parameter types for now.
    """
    sig = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }

    doc = inspect.getdoc(fn) or ""
    # Parse Args: section from docstring for per-parameter descriptions
    param_docs: dict[str, str] = {}
    in_args = False
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("args:"):
            in_args = True
            continue
        if in_args:
            if stripped and not stripped.startswith("-") and ":" in stripped:
                parts = stripped.split(":", 1)
                param_docs[parts[0].strip()] = parts[1].strip()
            elif stripped.lower() in ("returns:", "raises:", "example:"):
                in_args = False

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        py_type = (
            param.annotation
            if param.annotation != inspect.Parameter.empty
            else str
        )
        json_type = type_map.get(py_type, "string")

        prop: dict[str, Any] = {"type": json_type}
        if param_name in param_docs:
            prop["description"] = param_docs[param_name]

        properties[param_name] = prop

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }
