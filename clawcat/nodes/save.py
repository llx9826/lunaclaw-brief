"""Save node — persists used item IDs for cross-run deduplication."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from clawcat.schema.item import Item
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)

MEMORY_PATH = Path("data/item_memory.json")


def save_node(state: PipelineState) -> dict:
    """Save item_ids of items used in this run for future dedup."""
    items = state.get("filtered_items", [])
    if not items:
        return {}

    existing: dict = {}
    if MEMORY_PATH.exists():
        try:
            existing = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    seen_ids: list[str] = existing.get("seen_ids", [])
    new_ids = [item.item_id for item in items if item.item_id not in set(seen_ids)]
    seen_ids.extend(new_ids)

    MAX_MEMORY = 5000
    if len(seen_ids) > MAX_MEMORY:
        seen_ids = seen_ids[-MAX_MEMORY:]

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(
        json.dumps({"seen_ids": seen_ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Saved %d new item IDs (total: %d)", len(new_ids), len(seen_ids))
    return {}
