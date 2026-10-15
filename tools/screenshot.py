"""
tools/screenshot.py
===================
Screenshot capture tool.
"""

import datetime
from pathlib import Path

from tools.registry import register_tool
from config.settings import settings
from logger import get_logger

log = get_logger(__name__)


@register_tool(description="Take a screenshot of the current screen.")
def take_screenshot() -> str:
    """
    Capture the current screen and save it to the screenshots directory.

    Returns:
        Path to the saved screenshot file, or an error message.
    """
    import pyautogui

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    path = settings.screenshots_dir / filename

    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(str(path))
        log.info("Screenshot saved", extra={"path": str(path)})
        return f"Screenshot saved to {path}."
    except Exception as exc:
        log.error("Screenshot failed", extra={"error": str(exc)})
        return f"Failed to take screenshot: {exc}"


@register_tool(description="Analyze what is currently open or visible on the screen using AI vision.")
def analyze_screen(question: str = "Describe what is currently open on my screen.") -> str:
    """
    Capture the screen and ask the vision model to analyze what is visible.

    Args:
        question: Specific question about the screen contents (e.g. 'Where is the download button?').

    Returns:
        Natural language description of the screen or targeted element.
    """
    import base64
    import io
    import pyautogui
    from openai import OpenAI

    log.info("Analyzing screen", extra={"question": question})

    try:
        screenshot = pyautogui.screenshot()
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")

        client = OpenAI(api_key=settings.llm_api_key)
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_img}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        answer = response.choices[0].message.content or "No response from vision model."
        return answer.strip()
    except Exception as exc:
        log.error("Vision analysis failed", extra={"error": str(exc)})
        return f"Failed to analyze screen: {exc}"
