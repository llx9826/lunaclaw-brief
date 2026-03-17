"""LunaClaw Brief — Item Memory Store (L1)

Tracks previously used content items by item_id to prevent the same
article / repo / news from appearing in consecutive issues.

Refactored from brief/dedup.py with key improvement:
  - Preset-scoped namespacing: each preset maintains its own usage pool,
    so AI-weekly and finance-daily don't interfere with each other.

Storage: data/item_memory.json
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from brief.models import Item
from brief.memory.protocol import MemoryStore


class ItemStore(MemoryStore):
    """L1 memory — item-level deduplication with preset isolation."""

    name = "items"

    def __init__(self, data_dir: Path, **kwargs):
        super().__init__(data_dir, **kwargs)
        self._path = data_dir / "item_memory.json"
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _scoped_key(self, preset: str, item_id: str) -> str:
        return f"{preset}:{item_id}"

    def filter_items(
        self,
        items: list[Item],
        preset: str,
        window_days: int = 30,
    ) -> list[Item]:
        """Filter out items used within window_days for this preset."""
        cutoff = (datetime.now() - timedelta(days=window_days)).isoformat()
        result: list[Item] = []
        for item in items:
            key = self._scoped_key(preset, item.item_id)
            record = self._data.get(key)
            if record is None or record.get("used_at", "") < cutoff:
                result.append(item)
        return result

    def recall(self, preset: str, n: int = 5) -> dict:
        """Return recently used item IDs for this preset."""
        prefix = f"{preset}:"
        entries = [
            {"item_id": k[len(prefix):], **v}
            for k, v in self._data.items()
            if k.startswith(prefix)
        ]
        entries.sort(key=lambda e: e.get("used_at", ""), reverse=True)
        return {"recent_items": entries[:n]}

    def save(
        self,
        preset: str,
        issue_label: str,
        items: list[Item],
        markdown: str,
    ):
        """Record items as used for this preset."""
        now = datetime.now().isoformat()
        for item in items:
            key = self._scoped_key(preset, item.item_id)
            self._data[key] = {
                "title": item.title[:80],
                "source": item.source,
                "used_at": now,
                "issue_label": issue_label,
            }
        self._save()
