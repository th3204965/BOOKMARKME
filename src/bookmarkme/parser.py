"""Parse and generate Netscape Bookmark HTML files."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_bookmarks(html: str) -> dict[str, Any]:
    """Parse a Netscape Bookmark HTML file into a structured dict.

    Uses regex-based parsing to handle the quirky Netscape bookmark format
    where tags like <DT> and <DL> are not properly closed.

    Returns:
        A root folder dict with nested children (folders and bookmarks).
    """
    # Tokenize: extract meaningful tags in order
    # We care about: <DL>, </DL>, <DT><H3>...</H3>, <DT><A HREF="...">...</A>
    tokens: list[dict[str, Any]] = []

    # Match folder headers: <DT><H3 ...>Title</H3>
    # Match bookmarks: <DT><A HREF="url" ...>Title</A>
    # Match DL open/close
    tag_pattern = re.compile(
        r"<DL>|</DL>|<DT><H3[^>]*>(.*?)</H3>|<DT><A\s+HREF=\"([^\"]*?)\"[^>]*>(.*?)</A>",
        re.IGNORECASE | re.DOTALL,
    )

    for match in tag_pattern.finditer(html):
        text = match.group(0).upper()
        if text.startswith("<DL>"):
            tokens.append({"type": "dl_open"})
        elif text.startswith("</DL>"):
            tokens.append({"type": "dl_close"})
        elif match.group(1) is not None:
            tokens.append({"type": "folder", "name": _unescape(match.group(1).strip())})
        elif match.group(2) is not None:
            tokens.append(
                {
                    "type": "bookmark",
                    "url": match.group(2).strip(),
                    "title": _unescape(match.group(3).strip()),
                }
            )

    # Build tree from token stream
    root: dict[str, Any] = {"name": "Bookmarks", "type": "folder", "children": []}
    stack: list[dict[str, Any]] = [root]
    pending_folder: str | None = None

    for token in tokens:
        if token["type"] == "folder":
            # A folder header — the next DL_OPEN creates this folder
            pending_folder = token["name"]

        elif token["type"] == "dl_open":
            folder_name = pending_folder or "Bookmarks"
            pending_folder = None

            # If we already have the root, create a new subfolder
            if len(stack) > 1 or stack[0]["children"] or folder_name != "Bookmarks":
                new_folder: dict[str, Any] = {
                    "name": folder_name,
                    "type": "folder",
                    "children": [],
                }
                stack[-1]["children"].append(new_folder)
                stack.append(new_folder)
            else:
                # This is the root DL
                stack[0]["name"] = folder_name if folder_name != "Bookmarks" else "Bookmarks"

        elif token["type"] == "dl_close":
            if len(stack) > 1:
                stack.pop()

        elif token["type"] == "bookmark" and token["url"]:
            stack[-1]["children"].append(
                {
                    "title": token["title"] or "Untitled",
                    "url": token["url"],
                    "type": "bookmark",
                }
            )

    return root


def _unescape(text: str) -> str:
    """Unescape HTML entities in parsed text."""
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )


def bookmarks_to_json(bookmarks: dict[str, Any]) -> str:
    """Convert parsed bookmark structure to a JSON string for the AI model."""
    return json.dumps(bookmarks, indent=2, ensure_ascii=False)


def json_to_bookmarks(json_str: str) -> dict[str, Any]:
    """Parse a JSON string back into a bookmark structure."""
    return json.loads(json_str)


def generate_bookmarks_html(bookmarks: dict[str, Any]) -> str:
    """Generate a valid Netscape Bookmark HTML file from a bookmark structure.

    Args:
        bookmarks: A folder dict with 'name', 'type', and 'children' keys.

    Returns:
        A string containing valid Netscape Bookmark HTML.
    """
    lines: list[str] = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file.",
        "     It will be read and overwritten.",
        "     DO NOT EDIT! -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
    ]

    def _render_folder(folder: dict[str, Any], indent: int = 0) -> None:
        """Recursively render a folder and its children as HTML."""
        prefix = "    " * indent

        lines.append(f"{prefix}<DL><p>")

        for child in folder.get("children", []):
            if child.get("type") == "folder":
                lines.append(f"{prefix}    <DT><H3>{_escape(child['name'])}</H3>")
                _render_folder(child, indent + 1)
            elif child.get("type") == "bookmark":
                url = _escape(child.get("url", ""))
                title = _escape(child.get("title", "Untitled"))
                lines.append(f'{prefix}    <DT><A HREF="{url}">{title}</A>')

        lines.append(f"{prefix}</DL><p>")

    _render_folder(bookmarks)

    return "\n".join(lines) + "\n"


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def count_bookmarks(bookmarks: dict[str, Any]) -> int:
    """Count the total number of bookmarks (not folders) in the structure."""
    count = 0
    for child in bookmarks.get("children", []):
        if child.get("type") == "bookmark":
            count += 1
        elif child.get("type") == "folder":
            count += count_bookmarks(child)
    return count
