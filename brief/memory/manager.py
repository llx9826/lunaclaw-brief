"""LunaClaw Brief — Memory Manager (Facade)

Composes multiple MemoryStore backends and provides a single entry point
for the Pipeline to interact with the memory system.

Usage:
    manager = MemoryManager.create_default(data_dir, llm=llm_client)
    filtered = manager.filter_items(items, preset="ai_weekly", window_days=30)
    memories = manager.recall_all(preset="ai_weekly")
    manager.save_all(preset="ai_weekly", issue_label="2026-03-17", items=items, markdown=md)
"""

from __future__ import annotations

from pathlib import Path

from brief.models import Item
from brief.memory.protocol import MemoryStore
from brief.memory.item_store import ItemStore
from brief.memory.content_store import ContentStore
from brief.memory.topic_store import TopicStore


class MemoryManager:
    """Facade that composes multiple MemoryStores.

    Pipeline uses this single entry point — never touches individual stores.
    Stores are registered via register() and processed in registration order.
    """

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._stores: list[MemoryStore] = []

    def register(self, store: MemoryStore) -> "MemoryManager":
        """Register a memory store. Returns self for chaining."""
        self._stores.append(store)
        return self

    @property
    def stores(self) -> list[MemoryStore]:
        return list(self._stores)

    def filter_items(
        self,
        items: list[Item],
        preset: str,
        window_days: int = 30,
    ) -> list[Item]:
        """Chain all stores' item filters. Order matters: L1 -> L2."""
        for store in self._stores:
            items = store.filter_items(items, preset, window_days)
        return items

    def recall_all(self, preset: str) -> dict:
        """Gather memories from all stores, keyed by store.name."""
        return {store.name: store.recall(preset) for store in self._stores}

    def save_all(
        self,
        preset: str,
        issue_label: str,
        items: list[Item],
        markdown: str,
    ):
        """Persist new memories to all stores."""
        for store in self._stores:
            store.save(preset, issue_label, items, markdown)

    @classmethod
    def create_default(cls, data_dir: Path, llm=None) -> "MemoryManager":
        """Factory: create a manager with the standard L1/L2/L3 stores.

        Registration order determines filter_items chain priority:
          L1 ItemStore  → hard dedup by item_id
          L2 TopicStore → soft reorder by theme overlap
          (L3 ContentStore does not filter items, only injects prompt constraints)
        """
        manager = cls(data_dir)
        manager.register(ItemStore(data_dir))
        manager.register(TopicStore(data_dir))
        manager.register(ContentStore(data_dir, llm=llm))
        return manager
