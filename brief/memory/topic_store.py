"""LunaClaw Brief — Topic Memory Store (L2)

Tracks theme / topic fingerprints across issues to prevent consecutive
reports from covering the same macro themes (e.g. three issues in a row
about "大模型取代小模型").

Approach:
  - Extract top keywords from selected items' titles + raw_text
  - Compute a "topic fingerprint" = top-N keywords + domain tags
  - On filter: compute Jaccard similarity with recent fingerprints;
    deprioritize items that push similarity above threshold
  - On recall: return recent topic fingerprints for LLM diversity hints

Pure Python, no external dependencies (uses collections.Counter).

Storage: data/topic_memory.json
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from brief.models import Item
from brief.memory.protocol import MemoryStore

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need",
    "of", "in", "to", "for", "with", "on", "at", "from", "by",
    "up", "about", "into", "over", "after", "and", "but", "or",
    "as", "if", "then", "than", "so", "no", "not", "only", "very",
    "it", "its", "this", "that", "these", "those", "i", "we", "you",
    "he", "she", "they", "me", "him", "her", "us", "them", "my",
    "your", "his", "our", "their", "what", "which", "who", "when",
    "where", "how", "all", "each", "every", "both", "few", "more",
    "new", "old", "using", "based", "via", "use", "used",
    "的", "了", "在", "是", "和", "与", "对", "等", "也",
    "将", "已", "被", "从", "到", "中", "上", "下", "一",
    "个", "为", "不", "有", "这", "那", "就", "都", "把",
})

_WORD_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[a-z][a-z0-9-]{2,}", re.IGNORECASE)


class TopicStore(MemoryStore):
    """L2 memory — topic-level dedup via keyword fingerprinting."""

    name = "topics"

    SIMILARITY_THRESHOLD = 0.35
    FINGERPRINT_SIZE = 15
    MAX_HISTORY = 10

    def __init__(self, data_dir: Path, **kwargs):
        super().__init__(data_dir, **kwargs)
        self._path = data_dir / "topic_memory.json"
        self._data: dict[str, list[dict]] = self._load()

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

    def recall(self, preset: str, n: int = 3) -> dict:
        """Return recent topic fingerprints for diversity hinting."""
        entries = self._data.get(preset, [])
        recent = entries[-n:] if entries else []
        return {"recent_topics": recent}

    def save(
        self,
        preset: str,
        issue_label: str,
        items: list[Item],
        markdown: str,
    ):
        """Extract and persist the topic fingerprint from selected items."""
        fingerprint = self._build_fingerprint(items)
        if not fingerprint:
            return

        tags: list[str] = []
        for item in items:
            tags.extend(item.meta.get("domain_tags", []))

        entry = {
            "issue_label": issue_label,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "keywords": fingerprint,
            "tags": list(set(tags)),
        }

        if preset not in self._data:
            self._data[preset] = []

        self._data[preset].append(entry)

        if len(self._data[preset]) > self.MAX_HISTORY:
            self._data[preset] = self._data[preset][-self.MAX_HISTORY:]

        self._save()

    def filter_items(
        self,
        items: list[Item],
        preset: str,
        window_days: int = 30,
    ) -> list[Item]:
        """Deprioritize items whose topics heavily overlap with recent issues.

        Instead of hard-filtering, moves high-overlap items to the end
        so they're less likely to be selected by the pipeline's top-K.
        """
        recent_entries = self._data.get(preset, [])
        if not recent_entries:
            return items

        recent_kw: set[str] = set()
        for entry in recent_entries[-3:]:
            recent_kw.update(entry.get("keywords", []))

        if not recent_kw:
            return items

        def overlap_score(item: Item) -> float:
            item_kw = set(self._tokenize(f"{item.title} {item.raw_text}"))
            if not item_kw:
                return 0.0
            return len(item_kw & recent_kw) / len(item_kw | recent_kw)

        scored = [(item, overlap_score(item)) for item in items]
        high_overlap = [
            (item, s) for item, s in scored if s >= self.SIMILARITY_THRESHOLD
        ]
        low_overlap = [
            (item, s) for item, s in scored if s < self.SIMILARITY_THRESHOLD
        ]

        return [item for item, _ in low_overlap] + [item for item, _ in high_overlap]

    def _build_fingerprint(self, items: list[Item]) -> list[str]:
        """Extract top-N keywords from item titles and descriptions."""
        text = " ".join(f"{item.title} {item.raw_text}" for item in items)
        tokens = self._tokenize(text)
        if not tokens:
            return []
        counter = Counter(tokens)
        return [word for word, _ in counter.most_common(self.FINGERPRINT_SIZE)]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Extract meaningful tokens (Chinese 2+ chars, English 3+ chars)."""
        words = _WORD_RE.findall(text.lower())
        return [w for w in words if w not in _STOPWORDS]

    @staticmethod
    def format_constraints(recent_topics: list[dict]) -> str:
        """Format recent topics into a prompt hint for diversity."""
        if not recent_topics:
            return ""

        lines = ["\n\n【近期选题 — 以下主题近期已覆盖，请优先选择新角度或新领域】"]
        for entry in recent_topics:
            label = entry.get("issue_label", "?")
            keywords = entry.get("keywords", [])[:8]
            tags = entry.get("tags", [])
            summary = "、".join(keywords[:5])
            if tags:
                summary += f"（{', '.join(tags[:3])}）"
            lines.append(f"- {label}：{summary}")

        lines.append("请尽量选择与以上不同的切入点和话题。")
        return "\n".join(lines)
