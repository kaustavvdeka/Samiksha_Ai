"""
tools/files.py
==============
File system tools.

Security:
  create_file and search_files are SAFE.
  delete_file and move_file are CONFIRMATION_REQUIRED (enforced by PermissionChecker).
"""

import os
from pathlib import Path

from tools.registry import register_tool
from logger import get_logger

log = get_logger(__name__)


@register_tool(description="Search for files matching a name pattern on the computer.")
def search_files(query: str, directory: str = "~") -> str:
    """
    Search for files whose names contain the query string.

    Args:
        query:     The filename pattern to search for (case-insensitive).
        directory: Root directory to search. Defaults to home directory (~).

    Returns:
        Formatted list of matching file paths, or a not-found message.
    """
    search_root = Path(directory).expanduser().resolve()
    log.info("Searching files", extra={"query": query, "root": str(search_root)})

    matches: list[str] = []
    query_lower = query.lower()

    try:
        for path in search_root.rglob("*"):
            if query_lower in path.name.lower():
                matches.append(str(path))
            if len(matches) >= 20:  # Limit results
                break
    except PermissionError:
        pass  # Skip directories we can't read

    if not matches:
        return f"No files found matching '{query}' in {search_root}."

    result = f"Found {len(matches)} file(s) matching '{query}':\n"
    result += "\n".join(f"  • {m}" for m in matches)
    return result


@register_tool(description="Open a file with its default application.")
def open_file(path: str) -> str:
    """
    Open a file using the system's default application.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        Confirmation or error message.
    """
    import subprocess, platform

    file_path = Path(path).expanduser().resolve()
    if not file_path.exists():
        return f"File not found: {path}"

    log.info("Opening file", extra={"path": str(file_path)})
    _os = platform.system()
    try:
        if _os == "Darwin":
            subprocess.Popen(["open", str(file_path)])
        elif _os == "Linux":
            subprocess.Popen(["xdg-open", str(file_path)])
        elif _os == "Windows":
            os.startfile(str(file_path))  # type: ignore
        return f"Opening {file_path.name}."
    except Exception as exc:
        return f"Failed to open {path}: {exc}"


@register_tool(description="Create a new text file with optional content.")
def create_file(path: str, content: str = "") -> str:
    """
    Create a new file at the given path with optional text content.

    Args:
        path:    Path where the file should be created.
        content: Initial text content (optional).

    Returns:
        Confirmation or error message.
    """
    file_path = Path(path).expanduser().resolve()
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        log.info("Created file", extra={"path": str(file_path)})
        return f"Created file: {file_path}."
    except Exception as exc:
        return f"Failed to create file {path}: {exc}"


@register_tool(description="Read the contents of a text file.")
def read_file(path: str) -> str:
    """
    Read and return the text content of a file.

    Args:
        path: Path to the file.

    Returns:
        File contents as a string, or an error message.
    """
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists():
        return f"File not found: {path}"
    try:
        content = file_path.read_text(encoding="utf-8")
        if len(content) > 2000:
            content = content[:2000] + "\n... (truncated)"
        return content
    except Exception as exc:
        return f"Failed to read {path}: {exc}"
