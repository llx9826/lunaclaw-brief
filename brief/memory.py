"""LunaClaw Brief — Backward-compatible memory alias.

This module is DEPRECATED. All memory logic has moved to the
brief.memory package (ContentStore, TopicStore, ItemStore, MemoryManager).

Kept only for backward compatibility.
"""

from brief.memory.content_store import ContentStore as ContentMemory  # noqa: F401

__all__ = ["ContentMemory"]
