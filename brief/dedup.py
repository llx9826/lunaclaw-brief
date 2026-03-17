"""LunaClaw Brief — Backward-compatible dedup aliases.

This module is DEPRECATED. All memory/dedup logic has moved to
the brief.memory package (ItemStore, TopicStore, ContentStore).

Kept only for backward compatibility with external scripts that may
import UsedItemStore or IssueCounter.
"""

from brief.memory.item_store import ItemStore as UsedItemStore  # noqa: F401

__all__ = ["UsedItemStore"]
