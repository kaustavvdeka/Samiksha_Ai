"""
tools/__init__.py
=================
Import all tool modules here to trigger their @register_tool decorators.

This is the ONLY file that needs to change when you add a new tool module.
Simply add an import and the tool registry picks it up automatically.
"""

# Core tools — all tools self-register via @register_tool on import
import tools.applications   # open_application, close_application
import tools.browser        # open_website, search_google, search_youtube, open_url
import tools.keyboard       # type_text, press_key
import tools.mouse          # click, move_mouse
import tools.screenshot     # take_screenshot
import tools.system         # get_current_time, get_system_info
import tools.files          # search_files, open_file, create_file, read_file

# Memory & Workflow tools (Milestone 6 & 7)
import tools.memory_tools
import tools.messaging         # send_whatsapp_message


from tools.registry import execute_tool, get_tool_schemas, get_tool_names, has_tool

__all__ = ["execute_tool", "get_tool_schemas", "get_tool_names", "has_tool"]
