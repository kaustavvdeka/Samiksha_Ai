"""
tools/memory_tools.py
=====================
Memory and custom workflow tools exposed to the LLM agent.

Enables the agent to:
  - Remember facts and preferences across conversations (Milestone 6)
  - Recall saved project paths, user preferences, notes
  - Create and execute custom multi-step workflows (Milestone 7)
"""

import json
from typing import Any

from memory.memory import Memory
from tools.registry import register_tool, execute_tool
from logger import get_logger

log = get_logger(__name__)

# Shared memory instance for tools
_memory = Memory()


@register_tool(description="Save a persistent fact, preference, or project path in memory.")
def save_memory(key: str, value: str, category: str = "general") -> str:
    """
    Store a fact in long-term memory for later recall.

    Args:
        key:      A short identifier (e.g. 'main_project', 'favorite_browser', 'workspace').
        value:    The content to remember (e.g. '/path/to/project', 'Brave').
        category: Optional category for grouping (e.g. 'projects', 'preferences').

    Returns:
        Confirmation message.
    """
    return _memory.remember(key=key, value=value, category=category)


@register_tool(description="Recall a stored fact or preference from memory by its exact key.")
def get_memory(key: str) -> str:
    """
    Retrieve a fact stored in memory.

    Args:
        key: The key used when the memory was stored (e.g. 'main_project').

    Returns:
        The remembered value, or a message indicating the key was not found.
    """
    value = _memory.recall(key)
    if value is not None:
        return f"Memory for '{key}': {value}"
    return f"I do not have any memory saved for '{key}'."


@register_tool(description="Search stored memories by keyword across all keys and values.")
def search_memory(keyword: str) -> str:
    """
    Search long-term memory for any facts containing a keyword.

    Args:
        keyword: Search term to look for.

    Returns:
        List of matching memory entries.
    """
    return _memory.find(keyword)


@register_tool(description="List all stored memories, optionally filtered by category.")
def list_memories(category: str = "") -> str:
    """
    List all facts currently saved in memory.

    Args:
        category: Optional category filter (leave empty for all).

    Returns:
        Formatted list of memories.
    """
    cat = category.strip() if category.strip() else None
    return _memory.list_all(category=cat)


@register_tool(description="Delete a fact from memory by key.")
def forget_memory(key: str) -> str:
    """
    Remove a specific memory item.

    Args:
        key: Key of the memory item to delete.

    Returns:
        Confirmation message.
    """
    return _memory.forget(key)


@register_tool(description="Save a custom multi-step workflow command.")
def save_custom_workflow(name: str, steps_json: str, description: str = "") -> str:
    """
    Save a sequence of tool actions as a named custom workflow.

    Args:
        name:        Name of the workflow (e.g. 'start coding', 'start ml environment').
        steps_json:  JSON string of steps, e.g. '[{"tool": "open_application", "arguments": {"application": "VS Code"}}]'
        description: Short human description of what this workflow does.

    Returns:
        Confirmation message or error.
    """
    try:
        steps = json.loads(steps_json)
        if not isinstance(steps, list):
            return "Error: steps_json must be a JSON array of objects with 'tool' and 'arguments'."
        return _memory.save_workflow(name=name, steps=steps, description=description)
    except Exception as exc:
        return f"Failed to save workflow: {exc}"


@register_tool(description="Execute a previously saved custom workflow by name.")
def execute_custom_workflow(name: str) -> str:
    """
    Run all steps in a saved custom workflow in sequence.

    Args:
        name: Name of the workflow to run (e.g. 'start coding').

    Returns:
        Summary of executed steps.
    """
    workflow = _memory.get_workflow(name)
    if not workflow:
        return f"Workflow '{name}' not found. Available workflows: {_memory.list_workflows()}"

    steps = workflow.get("steps", [])
    results: list[str] = []
    log.info("Executing custom workflow", extra={"name": name, "steps": len(steps)})

    for i, step in enumerate(steps, 1):
        tool = step.get("tool")
        arguments = step.get("arguments", {})
        if not tool:
            continue
        try:
            res = execute_tool(tool, arguments)
            results.append(f"Step {i} ({tool}): {res}")
        except Exception as exc:
            results.append(f"Step {i} ({tool}) failed: {exc}")

    return f"Completed workflow '{name}':\n" + "\n".join(results)


@register_tool(description="List all available custom workflows.")
def list_custom_workflows() -> str:
    """
    List names and descriptions of all saved custom workflows.

    Returns:
        Formatted list of workflows.
    """
    return _memory.list_workflows()
