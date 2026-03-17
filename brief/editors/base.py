"""LunaClaw Brief — Editor base class.

Abstract base for all editors, providing LLM invocation with:
  - Standard generate() with retry logic
  - Streaming generate_stream() that yields chunks
  - Memory-aware prompt construction (decoupled from memory stores)
"""

from __future__ import annotations

import time
import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generator

from brief.models import Item, ReportDraft, PresetConfig
from brief.llm import LLMClient

_WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class BaseEditor(ABC):
    """Base class for all editors, providing LLM invocation and retry logic.

    Memory integration:
      Editor receives a memory_context dict from Pipeline (keyed by store name).
      It formats constraints via _format_memory_prompt() and appends to the
      user prompt. Editor never imports or depends on any memory store directly.
    """

    def __init__(self, preset: PresetConfig, llm: LLMClient):
        self.preset = preset
        self.llm = llm

    def _estimate_max_tokens(self) -> int:
        """Estimate required max_tokens from target_word_count.

        Chinese text averages ~1.8 tokens/char; add 30% buffer for formatting.
        """
        hi = self.preset.target_word_count[1] if self.preset.target_word_count else 5000
        return max(int(hi * 2.2), 4000)

    def generate(
        self,
        items: list[Item],
        issue_label: str,
        user_hint: str = "",
        memory_context: dict | None = None,
    ) -> ReportDraft | None:
        """Generate a report draft with exponential-backoff retry."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(items, issue_label, user_hint)
        user_prompt += self._format_memory_prompt(memory_context)
        max_tokens = self._estimate_max_tokens()

        for attempt in range(3):
            try:
                response = self.llm.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                if not response:
                    self._backoff(attempt, "LLM returned empty")
                    continue

                markdown = self._clean_markdown(response)
                return ReportDraft(markdown=markdown, issue_label=issue_label)

            except Exception as e:
                self._backoff(attempt, str(e)[:60])

        return None

    def generate_stream(
        self,
        items: list[Item],
        issue_label: str,
        user_hint: str = "",
        memory_context: dict | None = None,
    ) -> Generator[str, None, None]:
        """Stream report generation, yielding Markdown chunks as they arrive."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(items, issue_label, user_hint)
        user_prompt += self._format_memory_prompt(memory_context)

        max_tokens = self._estimate_max_tokens()
        for chunk in self.llm.stream(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        ):
            yield chunk

    @abstractmethod
    def _build_system_prompt(self) -> str:
        ...

    @abstractmethod
    def _build_user_prompt(
        self, items: list[Item], issue_label: str, user_hint: str
    ) -> str:
        ...

    @staticmethod
    def _format_memory_prompt(memory_context: dict | None) -> str:
        """Convert memory_context dict into prompt constraint text.

        Delegates formatting to each store's static format_constraints()
        via a simple convention: import the formatter only if the key exists.
        This keeps the editor decoupled — it only knows the dict structure,
        not the store implementations.
        """
        if not memory_context:
            return ""

        parts: list[str] = []

        content_data = memory_context.get("content", {})
        past_claims = content_data.get("past_claims", [])
        if past_claims:
            from brief.memory.content_store import ContentStore
            parts.append(ContentStore.format_constraints(past_claims))

        topic_data = memory_context.get("topics", {})
        recent_topics = topic_data.get("recent_topics", [])
        if recent_topics:
            from brief.memory.topic_store import TopicStore
            parts.append(TopicStore.format_constraints(recent_topics))

        return "".join(parts)

    @staticmethod
    def _today_context() -> str:
        """Date string with weekday for LLM prompt (prevents weekday hallucination)."""
        now = datetime.now()
        return f"{now.strftime('%Y-%m-%d')}（{_WEEKDAY_CN[now.weekday()]}）"

    @staticmethod
    def _engagement_rules(target_audience: str = "") -> str:
        """Content engagement enhancement rules for LLM prompts."""
        rules = """【内容吸引力要求】
- Hook 开头：每个章节第一句用数据、反常识或冲突开场
- 对比锚定：比较时给参照物（"相比 GPT-4o 快 3 倍"而非"速度快"）
- 数据高亮：关键数字用 **加粗**（如 **+12.5%**、**$3.2B**）
- 悬念收尾：章节末尾留一个值得关注的后续问题"""
        if target_audience:
            rules += f"\n- 目标读者：{target_audience}，用该受众熟悉的术语和视角"
        return rules

    @staticmethod
    def _clean_markdown(response: str) -> str:
        """Strip markdown code fence wrappers from LLM response."""
        text = response.strip()
        if text.startswith("```markdown"):
            text = text[11:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    @staticmethod
    def _backoff(attempt: int, reason: str):
        delay = min(1.0 * (2 ** attempt), 30.0) + random.uniform(0, 1)
        print(f"   [{reason}], retrying in {delay:.1f}s ({attempt + 1}/3)...")
        time.sleep(delay)
