"""Organize bookmarks using the Gemini API."""

from __future__ import annotations

import json
from typing import Any

from google import genai
from rich.console import Console

from bookmarkme.parser import bookmarks_to_json, count_bookmarks, json_to_bookmarks

console = Console()

SYSTEM_PROMPT = """\
You are an expert bookmark organizer. You will receive a JSON structure representing \
a user's browser bookmarks (exported from Chrome/Firefox/etc.).

Your job is to reorganize them into a clean, logical folder hierarchy. Follow these rules:

1. **Categorize** bookmarks into clear, descriptive folders. Use categories like:
   - Development (Programming, APIs, Documentation, Tools)
   - Design (UI/UX, Inspiration, Assets)
   - Social Media
   - News & Media
   - Entertainment (Videos, Music, Games)
   - Education & Learning
   - Shopping & Finance
   - Productivity & Tools
   - Reference & Research
   - Personal
   - Other
   Only create folders that have bookmarks in them. Feel free to create sub-folders \
   for large categories.

2. **Remove duplicates**: If the same URL appears multiple times, keep only one copy \
   (prefer the one with the better title).

3. **Clean up titles**: Fix garbled, truncated, or unhelpful bookmark titles. Make them \
   concise but descriptive. For example:
   - "GitHub - user/repo: A tool for..." → "user/repo — A tool for..."
   - "untitled" or empty titles → Generate a meaningful title from the URL

4. **Sort** bookmarks alphabetically within each folder.

5. **Preserve all bookmarks**: Do NOT remove any bookmarks (except duplicates). \
   Every unique URL from the input must appear in the output.

6. **Output format**: Return ONLY valid JSON matching the exact input schema:
   - Folders: {"name": "...", "type": "folder", "children": [...]}
   - Bookmarks: {"title": "...", "url": "...", "type": "bookmark"}
   - The root must be a single folder named "Bookmarks"

Return ONLY the JSON. No explanations, no markdown, no code fences.
"""


def organize_bookmarks(
    bookmarks: dict[str, Any],
    api_key: str,
    model: str = "gemini-3.1-pro",
) -> dict[str, Any]:
    """Send bookmarks to Gemini for intelligent reorganization.

    Args:
        bookmarks: Parsed bookmark structure (from parser.parse_bookmarks).
        api_key: Google AI API key.
        model: Gemini model to use.

    Returns:
        Reorganized bookmark structure.

    Raises:
        ValueError: If the API response cannot be parsed as valid bookmarks.
        RuntimeError: If the API call fails.
    """
    bookmark_count = count_bookmarks(bookmarks)
    bookmark_json = bookmarks_to_json(bookmarks)

    console.print(f"\n[bold blue]📚 Sending {bookmark_count} bookmarks to {model}...[/bold blue]")

    client = genai.Client(api_key=api_key)

    try:
        user_message = (
            f"Here are my bookmarks in JSON format. Please reorganize them:\n\n{bookmark_json}"
        )
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=65536,
            ),
        )
    except Exception as e:
        msg = f"Gemini API call failed: {e}"
        raise RuntimeError(msg) from e

    if not response.text:
        msg = "Gemini returned an empty response."
        raise ValueError(msg)

    # Clean up the response — strip markdown code fences if present
    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        # Remove ```json ... ``` wrapping
        lines = raw_text.split("\n")
        # Remove first and last lines (``` markers)
        lines = lines[1:-1]
        raw_text = "\n".join(lines)

    try:
        organized = json_to_bookmarks(raw_text)
    except json.JSONDecodeError as e:
        console.print("\n[bold red]❌ Failed to parse Gemini response as JSON[/bold red]")
        console.print(f"[dim]Raw response (first 500 chars):[/dim]\n{raw_text[:500]}")
        msg = f"Invalid JSON in Gemini response: {e}"
        raise ValueError(msg) from e

    # Validate the structure
    if not isinstance(organized, dict) or organized.get("type") != "folder":
        msg = "Gemini response is not a valid bookmark folder structure."
        raise ValueError(msg)

    new_count = count_bookmarks(organized)
    console.print(
        f"[bold green]✅ Reorganized! {bookmark_count} → {new_count} bookmarks "
        f"(after deduplication)[/bold green]"
    )

    return organized
