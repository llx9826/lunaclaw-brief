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
from typing import Generator

from brief.models import Item, ReportDraft, PresetConfig
from brief.llm import LLMClient


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

        for attempt in range(3):
            try:
                response = self.llm.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=8000,
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

        for chunk in self.llm.stream(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=8000,
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
