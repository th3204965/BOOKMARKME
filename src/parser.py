"""Parse and generate Netscape Bookmark HTML files."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


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


def _normalize_url(url: str) -> str:
    """Normalize a URL for stricter deduplication.

    Removes scheme (http/https), www prefix, trailing slashes, and utm_ parameters.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return url.lower().rstrip("/")

    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    if parsed.query:
        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        filtered_params = [(k, v) for k, v in query_params if not k.startswith("utm_")]
        new_query = urlencode(filtered_params)
    else:
        new_query = ""

    path = parsed.path.rstrip("/")
    # Reconstruct without scheme to match http and https identical URLs
    normalized = urlunparse(("", netloc, path, parsed.params, new_query, ""))
    return normalized


def extract_and_deduplicate_bookmarks(bookmarks: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten the bookmark structure and remove duplicates by URL."""
    seen_urls: set[str] = set()
    flat_bookmarks: list[dict[str, str]] = []

    def _traverse(node: dict[str, Any]) -> None:
        if node.get("type") == "bookmark":
            url = node.get("url", "")
            if url and url.startswith("http"):
                local_patterns = ("localhost", "127.0.0.1", "192.168.", "10.0.0.")
                if not any(pattern in url for pattern in local_patterns):
                    norm_url = _normalize_url(url)
                    if norm_url not in seen_urls:
                        seen_urls.add(norm_url)
                        # Keep original title and url
                        flat_bookmarks.append(
                            {
                                "title": node.get("title", "Untitled"),
                                "url": url,
                                "type": "bookmark",
                            }
                        )
        for child in node.get("children", []):
            _traverse(child)

    _traverse(bookmarks)
    return flat_bookmarks
