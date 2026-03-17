"""LunaClaw Brief — Pluggable Memory System

Three-level memory architecture for cross-issue deduplication:

  L1 ItemStore    — item_id based, prevents same article/repo reuse
  L2 TopicStore   — keyword fingerprint, prevents same theme coverage
  L3 ContentStore — claim extraction, prevents same viewpoint repetition

All stores implement the MemoryStore protocol and are composed by
MemoryManager, which serves as the single entry point for Pipeline.

Usage:
    from brief.memory import MemoryManager

    manager = MemoryManager.create_default(data_dir, llm=llm_client)
    filtered = manager.filter_items(items, "ai_weekly", window_days=30)
    memories = manager.recall_all("ai_weekly")
    manager.save_all("ai_weekly", "2026-03-17", items, markdown)
"""

from brief.memory.protocol import MemoryStore
from brief.memory.item_store import ItemStore
from brief.memory.content_store import ContentStore
from brief.memory.topic_store import TopicStore
from brief.memory.manager import MemoryManager

__all__ = [
    "MemoryStore",
    "MemoryManager",
    "ItemStore",
    "ContentStore",
    "TopicStore",
]
