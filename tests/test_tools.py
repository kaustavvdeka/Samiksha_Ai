"""
tests/test_tools.py
===================
Unit tests for the tool registry and individual tools.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestToolRegistry:
    """Tests for the tool registry mechanics."""

    def test_all_tools_registered(self):
        """All expected tool names must be present after package import."""
        import tools  # triggers all @register_tool decorators
        from tools.registry import get_tool_names

        expected = [
            "open_application",
            "close_application",
            "open_website",
            "open_url",
            "search_google",
            "search_youtube",
            "type_text",
            "press_key",
            "click",
            "move_mouse",
            "take_screenshot",
            "get_current_time",
            "get_system_info",
            "search_files",
            "open_file",
            "create_file",
            "read_file",
            "save_memory",
            "get_memory",
            "search_memory",
            "list_memories",
            "forget_memory",
            "save_custom_workflow",
            "execute_custom_workflow",
            "list_custom_workflows",
            "analyze_screen",
        ]
        registered = get_tool_names()
        for name in expected:
            assert name in registered, f"Tool '{name}' not registered"

    def test_unknown_tool_raises_key_error(self):
        import tools
        from tools.registry import execute_tool

        with pytest.raises(KeyError):
            execute_tool("nonexistent_tool_xyz", {})

    def test_schema_format(self):
        """Tool schemas must be in OpenAI function-calling format."""
        import tools
        from tools.registry import get_tool_schemas

        schemas = get_tool_schemas()
        assert len(schemas) > 0
        for schema in schemas:
            assert schema["type"] == "function"
            assert "function" in schema
            fn = schema["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn


class TestGetCurrentTime:
    def test_returns_string(self):
        import tools
        from tools.registry import execute_tool

        result = execute_tool("get_current_time", {})
        assert isinstance(result, str)
        assert len(result) > 0


class TestSearchFiles:
    def test_nonexistent_search(self, tmp_path):
        import tools
        from tools.registry import execute_tool

        result = execute_tool(
            "search_files",
            {"query": "zzzneverexistszzz", "directory": str(tmp_path)},
        )
        assert "No files found" in result

    def test_finds_existing_file(self, tmp_path):
        import tools
        from tools.registry import execute_tool

        # Create a temp file to find
        (tmp_path / "samiksha_test_file.py").write_text("print('hello')")
        result = execute_tool(
            "search_files",
            {"query": "samiksha_test_file", "directory": str(tmp_path)},
        )
        assert "samiksha_test_file.py" in result


class TestCreateReadFile:
    def test_create_and_read(self, tmp_path):
        import tools
        from tools.registry import execute_tool

        file_path = str(tmp_path / "test_note.txt")
        create_result = execute_tool(
            "create_file",
            {"path": file_path, "content": "Hello Samiksha"},
        )
        assert "Created" in create_result

        read_result = execute_tool("read_file", {"path": file_path})
        assert "Hello Samiksha" in read_result


class TestOpenApplication:
    def test_returns_string_on_success(self):
        import tools
        from tools.registry import execute_tool

        mock_res = MagicMock()
        mock_res.returncode = 0
        with patch("subprocess.run", return_value=mock_res):
            result = execute_tool("open_application", {"application": "Brave"})
        assert "Opening Brave" in result

    def test_returns_useful_error_when_not_found(self):
        import tools
        from tools.registry import execute_tool

        mock_res = MagicMock()
        mock_res.returncode = 1
        with patch("subprocess.run", return_value=mock_res):
            result = execute_tool("open_application", {"application": "NonExistentAppXYZ"})
        assert "couldn't find NonExistentAppXYZ" in result


class TestBrowserTools:
    def test_search_google_returns_string(self):
        import tools
        from tools.registry import execute_tool

        with patch("webbrowser.open") as mock_open:
            result = execute_tool("search_google", {"query": "Swin Transformer"})
        assert "Swin Transformer" in result

    def test_search_youtube_returns_string(self):
        import tools
        from tools.registry import execute_tool

        with patch("webbrowser.open") as mock_open:
            result = execute_tool("search_youtube", {"query": "machine learning"})
        assert "machine learning" in result


class TestScreenshotAndVision:
    def test_take_screenshot_success(self, tmp_path):
        import tools
        from tools.registry import execute_tool

        mock_img = MagicMock()
        with patch("pyautogui.screenshot", return_value=mock_img):
            result = execute_tool("take_screenshot", {})
        assert "Screenshot saved" in result

    def test_analyze_screen_success(self):
        import tools
        from tools.registry import execute_tool

        mock_img = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "A desktop showing VS Code and a terminal window."
        mock_response = MagicMock(choices=[mock_choice])

        with patch("pyautogui.screenshot", return_value=mock_img):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                result = execute_tool(
                    "analyze_screen",
                    {"question": "What is currently open on my screen?"},
                )

        assert "VS Code and a terminal" in result
