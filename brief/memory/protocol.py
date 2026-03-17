"""LunaClaw Brief — Memory Store Protocol

Abstract base class defining the pluggable memory backend interface.
All memory stores (ItemStore, ContentStore, TopicStore, custom) implement
this protocol so MemoryManager can compose them uniformly.

Design: Protocol-first, inspired by the existing _Registry pattern —
each store is a self-contained unit with no cross-store dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from brief.models import Item


class MemoryStore(ABC):
    """Pluggable memory backend protocol.

    Lifecycle within Pipeline:
      1. filter_items() — called during Dedup phase to prune inputs
      2. recall()       — called before Edit phase to build LLM constraints
      3. save()         — called after Edit phase to persist new memories
    """

    name: str = "base"

    def __init__(self, data_dir: Path, **kwargs):
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def recall(self, preset: str, n: int = 5) -> dict:
        """Retrieve recent memories for the given preset.

        Returns a dict whose structure is store-specific. MemoryManager
        merges all stores' recall results keyed by store.name.
        """
        ...

    @abstractmethod
    def save(
        self,
        preset: str,
        issue_label: str,
        items: list[Item],
        markdown: str,
    ):
        """Persist new memories after a successful generation."""
        ...

    def filter_items(
        self,
        items: list[Item],
        preset: str,
        window_days: int = 30,
    ) -> list[Item]:
        """Optional item-level filtering during Dedup phase.

        Default implementation is a pass-through. Override in stores
        that need to prune items (e.g. ItemStore, TopicStore).
        """
        return items
