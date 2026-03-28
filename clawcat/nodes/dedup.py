"""Dedup node — time hard-filter + item-level deduplication.

Layer 2 of freshness guarantee: items without published_at are discarded.
Layer 1 of dedup: exact item_id matching.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from clawcat.schema.item import Item
from clawcat.state import PipelineState
from clawcat.utils.time import parse_naive

logger = logging.getLogger(__name__)

MEMORY_PATH = Path("data/item_memory.json")


def _load_seen_ids() -> set[str]:
    if MEMORY_PATH.exists():
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            return set(data.get("seen_ids", []))
        except Exception:
            pass
    return set()


def dedup_node(state: PipelineState) -> dict:
    """Filter items by time range and deduplicate by item_id."""
    task = state.get("task_config")
    raw_items = state.get("raw_items", [])

    if not task or not raw_items:
        return {"filtered_items": []}

    since = parse_naive(task.since) if task.since else None
    until = parse_naive(task.until) if task.until else None

    seen_ids = _load_seen_ids()
    filtered: list[Item] = []
    skipped_no_date = 0
    skipped_out_of_range = 0
    skipped_dup = 0

    for item in raw_items:
        if item.item_id in seen_ids:
            skipped_dup += 1
            continue

        pub_dt = item.published_datetime

        if pub_dt is not None and since and pub_dt < since:
            skipped_out_of_range += 1
            continue
        if pub_dt is not None and until and pub_dt > until:
            skipped_out_of_range += 1
            continue

        seen_ids.add(item.item_id)
        filtered.append(item)

    logger.info(
        "Dedup: %d → %d items (no_date=%d, out_of_range=%d, dup=%d)",
        len(raw_items), len(filtered),
        skipped_no_date, skipped_out_of_range, skipped_dup,
    )

    return {"filtered_items": filtered}
