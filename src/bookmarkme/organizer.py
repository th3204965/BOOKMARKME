"""Organize bookmarks using the Gemini API."""

from __future__ import annotations

import concurrent.futures
import json
import time
from typing import Any, Literal

from google import genai
from pydantic import BaseModel
from rich.console import Console

from bookmarkme.cache import load_cache, save_cache
from bookmarkme.parser import count_bookmarks, extract_and_deduplicate_bookmarks

console = Console()

CategoryEnum = Literal[
    "Development",
    "Design",
    "Social Media",
    "News & Media",
    "Entertainment",
    "Education & Learning",
    "Shopping & Finance",
    "Productivity & Tools",
    "Reference & Research",
    "Personal",
    "Other",
]


class BookmarkCategory(BaseModel):
    url: str
    category: CategoryEnum


class BookmarkCategoryList(BaseModel):
    items: list[BookmarkCategory]


CATEGORIES = [
    "Development (Programming, APIs, Documentation, Tools)",
    "Design (UI/UX, Inspiration, Assets)",
    "Social Media",
    "News & Media",
    "Entertainment (Videos, Music, Games)",
    "Education & Learning",
    "Shopping & Finance",
    "Productivity & Tools",
    "Reference & Research",
    "Personal",
    "Other",
]

SYSTEM_PROMPT = f"""\
You are an expert bookmark organizer. You will receive a JSON list of bookmarks containing 'title' \
and 'url'.

Your job is to categorize each bookmark into one of the following categories:
{chr(10).join(f"- {c}" for c in CATEGORIES)}

Rules:
1. Output ONLY a mapping of EXACT URLs to their assigned categories.
2. The category must be exactly one of the strings listed above. \
Use exactly the main category name like "Development", "Design", etc.
"""

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds


def _categorize_batch(
    client: genai.Client,
    model: str,
    batch: list[dict[str, str]],
) -> list[BookmarkCategory]:
    """Send a batch of bookmarks to Gemini for categorization with retry logic."""
    user_message = json.dumps(batch, indent=2, ensure_ascii=False)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=BookmarkCategoryList,
                ),
            )
        except Exception as e:
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                console.print(
                    f"[bold yellow]⚠️ Batch attempt {attempt}/{MAX_RETRIES} failed: {e}. "
                    f"Retrying in {delay}s...[/bold yellow]"
                )
                time.sleep(delay)
                continue
            console.print(f"[bold red]❌ Batch failed after {MAX_RETRIES} attempts: {e}[/bold red]")
            return []

        if not response.text:
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                console.print(
                    f"[bold yellow]⚠️ Empty response on attempt {attempt}/{MAX_RETRIES}. "
                    f"Retrying in {delay}s...[/bold yellow]"
                )
                time.sleep(delay)
                continue
            return []

        try:
            data = json.loads(response.text)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                items = []
            return [BookmarkCategory(**item) for item in items]
        except Exception as e:
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                console.print(
                    f"[bold yellow]⚠️ Parse error on attempt {attempt}/{MAX_RETRIES}: {e}. "
                    f"Retrying in {delay}s...[/bold yellow]"
                )
                time.sleep(delay)
                continue
            console.print(
                f"[bold yellow]⚠️ Failed to parse batch after {MAX_RETRIES} attempts: {e}"
                "[/bold yellow]"
            )
            return []

    return []  # unreachable, but keeps type-checkers happy


def organize_bookmarks(
    bookmarks: dict[str, Any],
    api_key: str,
    model: str = "gemini-2.5-pro",
    *,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Send bookmarks to Gemini for intelligent reorganization concurrently."""
    bookmark_count = count_bookmarks(bookmarks)

    # 1. Programmatic Deduplication
    flat_bookmarks = extract_and_deduplicate_bookmarks(bookmarks)
    new_count = len(flat_bookmarks)

    console.print(
        f"\n[bold blue]📚 Deduplicated: {bookmark_count} → {new_count} unique "
        "bookmarks.[/bold blue]"
    )

    if new_count == 0:
        return {"name": "Bookmarks", "type": "folder", "children": []}

    # 2. Load cache and split into cached vs. uncached bookmarks
    cache: dict[str, str] = load_cache() if use_cache else {}
    uncached_bookmarks: list[dict[str, str]] = []
    precached_count = 0

    for bm in flat_bookmarks:
        if bm["url"] in cache:
            precached_count += 1
        else:
            uncached_bookmarks.append(bm)

    if precached_count > 0:
        console.print(
            f"[bold green]⚡ {precached_count} bookmarks found in cache, "
            f"{len(uncached_bookmarks)} need categorization.[/bold green]"
        )

    # 3. Send only uncached bookmarks to Gemini
    if uncached_bookmarks:
        client = genai.Client(api_key=api_key)

        batch_size = 100
        batches = [
            uncached_bookmarks[i : i + batch_size]
            for i in range(0, len(uncached_bookmarks), batch_size)
        ]

        console.print(
            f"[bold blue]🚀 Sending {len(batches)} batch(es) of ≤{batch_size} "
            f"bookmarks to {model} concurrently...[/bold blue]"
        )

        all_categories: list[BookmarkCategory] = []

        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("[cyan]Categorizing bookmarks...", total=len(batches))
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(10, len(batches))
            ) as executor:
                futures = {
                    executor.submit(_categorize_batch, client, model, batch): batch
                    for batch in batches
                }

                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        all_categories.extend(result)
                    except Exception as e:
                        console.print(f"[bold red]❌ Batch failed unpredictably: {e}[/bold red]")
                    finally:
                        progress.advance(task_id)

        # Update cache with new results
        for item in all_categories:
            cache[item.url] = item.category

        if use_cache:
            save_cache(cache)
            console.print(f"[dim]💾 Cache updated ({len(cache)} total entries)[/dim]")

    # 4. Build url→category mapping from cache (covers both old and new)
    url_to_category = cache

    # 5. Reassemble nested folder structure
    category_folders: dict[str, list[dict[str, str]]] = {}

    for bm in flat_bookmarks:
        cat_full = url_to_category.get(bm["url"], "Other")
        cat_name = cat_full.split("(")[0].strip()

        if cat_name not in category_folders:
            category_folders[cat_name] = []
        category_folders[cat_name].append(bm)

    sorted_categories = sorted(category_folders.keys())

    root_children = []
    for cat in sorted_categories:
        sorted_bms = sorted(category_folders[cat], key=lambda x: x.get("title", "").lower())
        folder = {"name": cat, "type": "folder", "children": sorted_bms}
        root_children.append(folder)

    organized = {"name": "Bookmarks", "type": "folder", "children": root_children}

    final_count = count_bookmarks(organized)
    console.print(
        f"[bold green]✅ Reorganized completely! Final count: {final_count} bookmarks[/bold green]"
    )

    return organized
