"""
tools/keyboard.py
=================
Keyboard control tools using PyAutoGUI.

Isolated from the agent logic — only called through the tool registry.
"""

from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)


@register_tool(description="Type text using the keyboard.")
def type_text(text: str) -> str:
    """
    Type the given text using the keyboard at the current cursor position.

    Args:
        text: The text to type.

    Returns:
        Confirmation message.
    """
    import pyautogui
    import time

    log.info("Typing text", extra={"length": len(text)})
    time.sleep(0.3)  # Small delay to ensure focus
    pyautogui.typewrite(text, interval=0.05)
    return f"Typed: {text[:40]}{'...' if len(text) > 40 else ''}"


@register_tool(description="Press a keyboard key or key combination.")
def press_key(key: str) -> str:
    """
    Press a single key or a key combination.

    Args:
        key: Key name (e.g. "enter", "ctrl+c", "cmd+space", "escape").
             Use '+' to combine modifier keys.

    Returns:
        Confirmation message.
    """
    import pyautogui

    log.info("Pressing key", extra={"key": key})
    if "+" in key:
        keys = [k.strip() for k in key.split("+")]
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key)
    return f"Pressed key: {key}"
