"""
memory/memory.py
================
High-level memory interface used by the agent.

The agent calls:
    memory.remember("project_path", "~/projects/cropguard")
    memory.recall("project_path")
    memory.find("project")

This layer sits above the Database and adds:
  - Category handling
  - Workflow management
  - Conversation history management

Usage:
    from memory.memory import Memory
    mem = Memory()
    mem.remember("main_project", "~/projects/cropguard", category="projects")
    print(mem.recall("main_project"))
"""

from memory.database import Database
from logger import get_logger

log = get_logger(__name__)


class Memory:
    """
    High-level persistent memory for the Samiksha agent.

    All data is stored in SQLite and survives restarts.
    """

    def __init__(self) -> None:
        self.db = Database()

    # ------------------------------------------------------------------ #
    # Facts / Preferences
    # ------------------------------------------------------------------ #

    def remember(
        self, key: str, value: str, category: str = "general"
    ) -> str:
        """
        Store a fact in memory.

        Args:
            key:      A short identifier (e.g. "main_project", "user_name").
            value:    The value to remember.
            category: Optional grouping (e.g. "projects", "preferences").

        Returns:
            Confirmation string.
        """
        self.db.save_memory(key=key.lower(), value=value, category=category)
        log.info("Memory stored", extra={"key": key})
        return f"Got it. I'll remember that {key} is '{value}'."

    def recall(self, key: str) -> str | None:
        """
        Retrieve a stored fact by its exact key.

        Args:
            key: The key used when storing the fact.

        Returns:
            The stored value, or None if not found.
        """
        return self.db.get_memory(key.lower())

    def find(self, keyword: str) -> str:
        """
        Search memories by keyword (searches both keys and values).

        Args:
            keyword: Word or phrase to search for.

        Returns:
            Formatted list of matching memories, or not-found message.
        """
        results = self.db.search_memories(keyword)
        if not results:
            return f"I don't have any memory matching '{keyword}'."

        lines = [f"I found {len(results)} memory entry(s) for '{keyword}':"]
        for r in results:
            lines.append(f"  • {r['key']}: {r['value']}")
        return "\n".join(lines)

    def forget(self, key: str) -> str:
        """
        Delete a stored memory by key.

        Args:
            key: The key to forget.

        Returns:
            Confirmation string.
        """
        deleted = self.db.delete_memory(key.lower())
        if deleted:
            return f"Okay, I've forgotten '{key}'."
        return f"I don't have a memory for '{key}'."

    def list_all(self, category: str | None = None) -> str:
        """
        List all stored memories, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            Formatted list.
        """
        memories = self.db.list_memories(category)
        if not memories:
            return "I don't have any memories stored yet."

        header = f"Stored memories ({len(memories)}):"
        lines = [header]
        for m in memories:
            lines.append(f"  [{m['category']}] {m['key']}: {m['value']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Conversation history
    # ------------------------------------------------------------------ #

    def add_turn(self, role: str, content: str) -> None:
        """Record a conversation turn (user or assistant)."""
        self.db.add_conversation_turn(role, content)

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get recent conversation turns as a list of {role, content} dicts."""
        return self.db.get_recent_conversations(limit)

    def trim_history(self) -> None:
        """Remove old conversation turns, keeping the last 100."""
        self.db.clear_old_conversations(keep_last=100)

    # ------------------------------------------------------------------ #
    # Custom workflows
    # ------------------------------------------------------------------ #

    def save_workflow(
        self,
        name: str,
        steps: list[dict],
        description: str = "",
    ) -> str:
        """
        Save a named workflow (sequence of tool calls).

        Args:
            name:        Trigger phrase (e.g. "start coding").
            steps:       List of {"tool": ..., "arguments": {...}} dicts.
            description: Human-readable description.

        Returns:
            Confirmation message.
        """
        self.db.save_workflow(
            name=name.lower(),
            steps=steps,
            description=description,
        )
        return (
            f"Workflow '{name}' saved with {len(steps)} step(s)."
        )

    def get_workflow(self, name: str) -> dict | None:
        """Retrieve a workflow by name. Returns None if not found."""
        return self.db.get_workflow(name.lower())

    def list_workflows(self) -> str:
        """List all saved custom workflows."""
        workflows = self.db.list_workflows()
        if not workflows:
            return "No custom workflows saved yet."
        lines = ["Custom workflows:"]
        for w in workflows:
            desc = f" — {w['description']}" if w["description"] else ""
            lines.append(f"  • {w['name']}{desc}")
        return "\n".join(lines)
