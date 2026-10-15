"""
tools/mouse.py
==============
Mouse control tools using PyAutoGUI.
"""

from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)


@register_tool(description="Click at specific screen coordinates.")
def click(x: int, y: int) -> str:
    """
    Click the mouse at the given screen coordinates.

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.

    Returns:
        Confirmation message.
    """
    import pyautogui

    log.info("Mouse click", extra={"x": x, "y": y})
    pyautogui.click(x, y)
    return f"Clicked at ({x}, {y})."


@register_tool(description="Move the mouse to specific screen coordinates.")
def move_mouse(x: int, y: int) -> str:
    """
    Move the mouse cursor to the given screen coordinates.

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.

    Returns:
        Confirmation message.
    """
    import pyautogui

    log.info("Mouse move", extra={"x": x, "y": y})
    pyautogui.moveTo(x, y, duration=0.3)
    return f"Moved mouse to ({x}, {y})."
