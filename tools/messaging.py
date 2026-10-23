"""
tools/messaging.py
==================
Tools for sending messages via WhatsApp desktop, WhatsApp Web, and messaging gateways.

Features:
  - Direct integration with native macOS WhatsApp.app via whatsapp:// URI protocol
  - Automatically resolves contacts or user's phone from persistent Memory
  - Formats and normalizes international phone numbers
  - Auto-send via AppleScript Return key trigger or PyAutoGUI
  - Fallback to WhatsApp Web if desktop app is not present
  - Optional silent background delivery via CallMeBot API if configured in .env
"""

import os
import platform
import re
import subprocess
import time
import urllib.parse
from typing import Optional

from memory.memory import Memory
from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)

_OS = platform.system()  # "Darwin" | "Linux" | "Windows"
_memory = Memory()


def _clean_phone_number(raw_phone: str) -> str:
    """
    Normalise phone numbers: remove spaces, dashes, brackets.
    If 10 digits starting with 6-9, assume Indian mobile (+91).
    """
    clean = re.sub(r"[^0-9+]", "", raw_phone.strip())
    if clean.startswith("+"):
        clean = clean[1:]
    elif len(clean) == 10 and clean[0] in "6789":
        clean = "91" + clean
    return clean


def _resolve_recipient(recipient: str) -> tuple[Optional[str], str]:
    """
    Resolve recipient input (phone number, contact name, or 'me')
    to an international phone number and friendly display label.
    """
    rec_lower = recipient.strip().lower()

    # 1. User refers to themselves
    if rec_lower in ("", "me", "myself", "my phone", "my number", "my whatsapp", "personal"):
        saved = (
            _memory.recall("my_whatsapp")
            or _memory.recall("whatsapp")
            or _memory.recall("my_phone")
            or _memory.recall("phone_number")
        )
        if saved:
            return _clean_phone_number(saved), "your WhatsApp"
        return None, (
            "I don't know your WhatsApp number yet. Please provide your phone number, "
            "or say: 'Remember my WhatsApp number is +91XXXXXXXXXX'."
        )

    # 2. Direct phone number (contains 7 or more digits)
    digits_only = re.sub(r"[^0-9]", "", recipient)
    if len(digits_only) >= 7:
        clean = _clean_phone_number(recipient)
        return clean, f"+{clean}"

    # 3. Named contact in memory (e.g. "mom", "boss", "alex")
    saved_contact = (
        _memory.recall(f"{rec_lower}_whatsapp")
        or _memory.recall(f"{rec_lower}_phone")
        or _memory.recall(rec_lower)
    )
    if saved_contact:
        return _clean_phone_number(saved_contact), recipient.title()

    return None, f"Could not find a phone number for '{recipient}' in saved memory."


@register_tool(description="Send a WhatsApp message to a phone number or saved contact.")
def send_whatsapp_message(
    message: str,
    phone_number: str = "",
    auto_send: bool = True,
) -> str:
    """
    Send a WhatsApp message.

    Args:
        message:      The text message to send.
        phone_number: Recipient's phone number with country code (e.g. '+919876543210'),
                      contact name (e.g. 'Mom'), or leave blank/'me' to use saved user number.
        auto_send:    Whether to automatically press Send (default True).

    Returns:
        Status message confirming the message was sent or prepared.
    """
    if not message or not message.strip():
        return "Cannot send an empty message."

    clean_message = message.strip()
    phone, label = _resolve_recipient(phone_number)

    if not phone:
        return label  # Returns user-friendly explanation or memory prompt

    log.info(
        "Preparing WhatsApp message",
        extra={"recipient": label, "phone_masked": f"...{phone[-4:]}", "length": len(clean_message)},
    )

    # 1. Optional background delivery via CallMeBot API (if configured in .env)
    callmebot_key = os.getenv("CALLMEBOT_API_KEY")
    if callmebot_key and "your" in label.lower():
        try:
            import requests

            encoded_text = urllib.parse.quote(clean_message)
            api_url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={callmebot_key}"
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                return f"Sent WhatsApp message to {label} via background gateway: '{clean_message}'."
        except Exception as exc:
            log.warning("CallMeBot gateway failed, falling back to desktop app", extra={"error": str(exc)})

    # 2. Native desktop WhatsApp automation
    encoded_text = urllib.parse.quote(clean_message)
    whatsapp_uri = f"whatsapp://send?phone={phone}&text={encoded_text}"
    web_fallback_url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"

    launched = False
    if _OS == "Darwin":
        try:
            res = subprocess.run(["open", whatsapp_uri], capture_output=True, timeout=5)
            launched = res.returncode == 0
        except Exception:
            launched = False

    # Fallback to web browser if desktop protocol didn't launch
    if not launched:
        import webbrowser

        try:
            webbrowser.open(web_fallback_url)
            return (
                f"Opened WhatsApp Web chat for {label}. "
                f"Please press Send to deliver: '{clean_message}'."
            )
        except Exception as exc:
            return f"Failed to open WhatsApp: {exc}"

    # If auto_send is True, wait for WhatsApp to focus and press Return
    if auto_send:
        # Give WhatsApp a moment to bring the chat into focus
        time.sleep(1.8)

        # Method A: macOS AppleScript key code 36 (Return)
        if _OS == "Darwin":
            script = """
            tell application "System Events"
                tell process "WhatsApp"
                    key code 36
                end tell
            end tell
            """
            try:
                sub_res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
                if sub_res.returncode == 0:
                    return f"Sent WhatsApp message to {label}: '{clean_message}'."
            except Exception:
                pass

        # Method B: Cross-platform PyAutoGUI Enter
        try:
            import pyautogui

            pyautogui.press("enter")
            return f"Sent WhatsApp message to {label}: '{clean_message}'."
        except Exception:
            pass

    return (
        f"Opened WhatsApp conversation with {label} and entered your message. "
        "Press Enter to send."
    )
