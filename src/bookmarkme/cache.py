"""Local JSON cache for URL → category mappings."""

from __future__ import annotations

import json
from pathlib import Path

CACHE_FILE = Path.home() / ".bookmarkme" / "category_cache.json"


def load_cache() -> dict[str, str]:
    """Load cached URL→category mappings from disk."""
    if not CACHE_FILE.exists():
        return {}

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass

    return {}


def save_cache(cache: dict[str, str]) -> None:
    """Persist URL→category mappings to disk."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
