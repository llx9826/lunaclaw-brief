"""LunaClaw Brief — Content Memory Store (L3)

Tracks key claims / viewpoints from generated review sections to prevent
the LLM from repeating the same macro observations across consecutive
issues (e.g. "大模型逐渐取代小模型").

Lifecycle:
  Post-generation: extract key claims from review section -> save to JSON
  Pre-generation:  load recent claims -> inject as negative constraints

Refactored from brief/memory.py — now implements MemoryStore protocol.

Storage: data/content_memory.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from brief.models import Item
from brief.memory.protocol import MemoryStore


class ContentStore(MemoryStore):
    """L3 memory — viewpoint-level dedup via claim extraction."""

    name = "content"

    def __init__(self, data_dir: Path, llm=None, **kwargs):
        super().__init__(data_dir, **kwargs)
        self._path = data_dir / "content_memory.json"
        self._data: dict[str, list[dict]] = self._load()
        self._llm = llm

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
        """Load the last N issues' claims for this preset."""
        entries = self._data.get(preset, [])
        past = entries[-n:] if entries else []
        return {"past_claims": past}

    def save(
        self,
        preset: str,
        issue_label: str,
        items: list[Item],
        markdown: str,
    ):
        """Extract key claims from generated markdown and persist."""
        review_text = self._extract_review_section(markdown)
        if not review_text:
            return

        claims = self._extract_claims(review_text)
        if not claims:
            return

        entry = {
            "issue_label": issue_label,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "claims": claims,
            "review_snippet": review_text[:300],
        }

        if preset not in self._data:
            self._data[preset] = []

        self._data[preset].append(entry)

        if len(self._data[preset]) > 10:
            self._data[preset] = self._data[preset][-10:]

        self._save()

    @staticmethod
    def _extract_review_section(markdown: str) -> str:
        """Find the review / 复盘 / 快评 / 风险提示 section via regex."""
        patterns = [
            r"## .*(?:复盘|Claw 复盘).*?\n([\s\S]*?)(?=\n## |\Z)",
            r"## .*(?:快评|Claw 快评).*?\n([\s\S]*?)(?=\n## |\Z)",
            r"## .*(?:风险提示|Claw 风险|策略与风险).*?\n([\s\S]*?)(?=\n## |\Z)",
            r"## .*(?:趋势|展望).*?\n([\s\S]*?)(?=\n## |\Z)",
        ]
        for pat in patterns:
            m = re.search(pat, markdown)
            if m:
                return m.group(1).strip()
        return ""

    def _extract_claims(self, review_text: str) -> list[str]:
        """Extract 3-5 key claims. Uses LLM when available, else regex."""
        if self._llm:
            return self._extract_claims_llm(review_text)
        return self._extract_claims_regex(review_text)

    def _extract_claims_llm(self, review_text: str) -> list[str]:
        try:
            system = (
                "Extract 3-5 key claims/viewpoints from this review section. "
                "Each claim should be a concise Chinese sentence (<=30 chars). "
                "Return ONLY a JSON array of strings. Example: "
                '["观点一", "观点二", "观点三"]'
            )
            result = self._llm.classify(system, review_text[:1500])
            clean = result.strip().removeprefix("```json").removesuffix("```").strip()
            claims = json.loads(clean)
            if isinstance(claims, list) and all(isinstance(c, str) for c in claims):
                return claims[:5]
        except Exception:
            pass
        return self._extract_claims_regex(review_text)

    @staticmethod
    def _extract_claims_regex(review_text: str) -> list[str]:
        """Fallback: extract sentences from review as claims."""
        claims: list[str] = []
        for line in review_text.split("\n"):
            line = line.strip()
            line = re.sub(r"^#+\s*\d*\.?\s*", "", line)
            line = re.sub(r"^\*\*.*?\*\*\s*[:：]?\s*", "", line)
            line = re.sub(r"^[-*]\s*", "", line)
            if not line or len(line) < 10:
                continue
            sentences = re.split(r"[。；！]", line)
            for s in sentences:
                s = s.strip()
                if 10 <= len(s) <= 60:
                    claims.append(s)
        return claims[:5]

    @staticmethod
    def format_constraints(past_claims: list[dict]) -> str:
        """Format past claims into a prompt snippet for negative constraint injection.

        Called by Editor (via memory_context) to append constraints to user prompt.
        """
        if not past_claims:
            return ""

        lines = ["\n\n【历史观点 — 以下观点近期已表达过，请勿重复，务必提供新视角】"]
        for entry in past_claims:
            label = entry.get("issue_label", "?")
            claims = entry.get("claims", [])
            if claims:
                joined = "；".join(claims)
                lines.append(f"- {label} 期：{joined}")

        lines.append("请基于本期的具体素材，给出不同于以上的新观点和新判断。")
        return "\n".join(lines)
