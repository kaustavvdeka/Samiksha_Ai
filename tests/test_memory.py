"""
tests/test_memory.py
====================
Unit tests for the memory system and custom workflow tools.
"""

import json
import pytest
from memory.database import Database
from memory.memory import Memory


@pytest.fixture
def memory_instance():
    """Create a fresh in-memory database and Memory instance for testing."""
    db = Database(db_path=":memory:")
    mem = Memory()
    mem.db = db
    return mem


class TestDatabase:
    """Low-level SQLite database tests."""

    def test_save_and_get_memory(self):
        db = Database(db_path=":memory:")
        db.save_memory("key1", "value1", "category1")
        assert db.get_memory("key1") == "value1"

    def test_update_existing_memory(self):
        db = Database(db_path=":memory:")
        db.save_memory("key1", "value1")
        db.save_memory("key1", "value2")
        assert db.get_memory("key1") == "value2"

    def test_search_memories(self):
        db = Database(db_path=":memory:")
        db.save_memory("cropguard_project", "/path/to/cropguard")
        db.save_memory("weather_app", "/path/to/weather")
        results = db.search_memories("cropguard")
        assert len(results) == 1
        assert results[0]["key"] == "cropguard_project"

    def test_delete_memory(self):
        db = Database(db_path=":memory:")
        db.save_memory("key_to_del", "val")
        assert db.delete_memory("key_to_del") is True
        assert db.get_memory("key_to_del") is None
        assert db.delete_memory("nonexistent") is False

    def test_workflows(self):
        db = Database(db_path=":memory:")
        steps = [{"tool": "open_application", "arguments": {"application": "VS Code"}}]
        db.save_workflow("start coding", steps, "Launches coding environment")
        wf = db.get_workflow("start coding")
        assert wf is not None
        assert wf["name"] == "start coding"
        assert wf["steps"] == steps
        assert wf["description"] == "Launches coding environment"

    def test_conversation_history(self):
        db = Database(db_path=":memory:")
        db.add_conversation_turn("user", "Hello")
        db.add_conversation_turn("assistant", "Hi there")
        history = db.get_recent_conversations(10)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"


class TestMemory:
    """High-level Memory layer tests."""

    def test_remember_and_recall(self, memory_instance):
        memory_instance.remember("main_project", "~/projects/cropguard")
        val = memory_instance.recall("main_project")
        assert val == "~/projects/cropguard"

    def test_find_memory(self, memory_instance):
        memory_instance.remember("main_project", "~/projects/cropguard")
        result = memory_instance.find("cropguard")
        assert "cropguard" in result

    def test_forget_memory(self, memory_instance):
        memory_instance.remember("temp_note", "buy milk")
        res = memory_instance.forget("temp_note")
        assert "forgotten" in res
        assert memory_instance.recall("temp_note") is None

    def test_workflow_save_and_list(self, memory_instance):
        steps = [
            {"tool": "open_application", "arguments": {"application": "VS Code"}},
            {"tool": "open_website", "arguments": {"url": "https://github.com"}},
        ]
        save_res = memory_instance.save_workflow("dev setup", steps, "Open dev tools")
        assert "saved" in save_res
        wf = memory_instance.get_workflow("dev setup")
        assert wf is not None
        assert len(wf["steps"]) == 2

        list_res = memory_instance.list_workflows()
        assert "dev setup" in list_res


class TestMemoryTools:
    """Tests for tools in tools/memory_tools.py via the tool registry."""

    def test_memory_tools_registered(self):
        import tools
        from tools.registry import has_tool

        assert has_tool("save_memory")
        assert has_tool("get_memory")
        assert has_tool("search_memory")
        assert has_tool("list_memories")
        assert has_tool("forget_memory")
        assert has_tool("save_custom_workflow")
        assert has_tool("execute_custom_workflow")
        assert has_tool("list_custom_workflows")

    def test_execute_custom_workflow(self):
        import tools
        from tools.registry import execute_tool

        steps = [
            {"tool": "get_current_time", "arguments": {}}
        ]
        # Save workflow
        save_res = execute_tool(
            "save_custom_workflow",
            {
                "name": "check time workflow",
                "steps_json": json.dumps(steps),
                "description": "Workflow that checks the time",
            },
        )
        assert "saved" in save_res

        # Execute workflow
        exec_res = execute_tool(
            "execute_custom_workflow",
            {"name": "check time workflow"},
        )
        assert "Completed workflow" in exec_res
        assert "get_current_time" in exec_res
