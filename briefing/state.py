"""Bookkeeping for seen articles using data/seen.json."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
SEEN_FILE = DATA_DIR / "seen.json"


def article_id(url: str | None, title: str | None) -> str:
    """Generate a unique ID for an article using SHA-256 of normalized url or title."""
    text = url or title or ""
    # Normalize: lowercase, strip whitespace, remove protocol
    normalized = re.sub(r"^https?://", "", text.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def load_seen() -> dict[str, str]:
    """Load seen articles from data/seen.json."""
    if not SEEN_FILE.exists():
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load seen.json: {e}")
        return {}


def save_seen(seen: dict[str, str]) -> None:
    """Save seen articles to data/seen.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def filter_unseen(items: list[dict[str, Any]], seen: dict[str, str]) -> list[dict[str, Any]]:
    """Filter out items that have already been seen."""
    unseen = []
    for item in items:
        item_id = article_id(item.get("url"), item.get("title"))
        if item_id not in seen:
            item["_id"] = item_id
            unseen.append(item)
    return unseen


def mark_seen(
    items: list[dict[str, Any]], seen: dict[str, str], today_iso: str
) -> dict[str, str]:
    """
    Add today's items to seen dict and prune entries older than 14 days.
    Returns the updated seen dict.
    """
    # Add new items
    for item in items:
        item_id = item.get("_id") or article_id(item.get("url"), item.get("title"))
        seen[item_id] = today_iso

    # Prune old entries
    cutoff = (datetime.fromisoformat(today_iso) - timedelta(days=14)).isoformat()[:10]
    pruned = {k: v for k, v in seen.items() if v >= cutoff}

    logger.info(f"Marked {len(items)} items as seen, pruned {len(seen) - len(pruned)} old entries")
    return pruned
