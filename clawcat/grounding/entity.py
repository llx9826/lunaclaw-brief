"""Entity grounding — verifies entity names exist in source items."""

from __future__ import annotations

import re

from clawcat.grounding.protocol import GroundingChecker, GroundingIssue, GroundingResult
from clawcat.schema.item import Item


class EntityGrounder(GroundingChecker):
    """Checks that key entities in the report appear in source data."""

    name = "entity"

    _ENTITY_RE = re.compile(
        r"(?:【|《)([^】》]+)(?:】|》)|"
        r"\*\*([^*]{2,40})\*\*|"
        r'\"([^"]{2,40})\"'
    )

    _SKIP_LABELS = frozenset({
        "涨跌幅", "驱动因素", "事件概要", "核心创新", "研究问题", "实验结果",
        "内容概要", "背景脉络", "实际影响", "投资逻辑", "市场反应",
        "Claw 锐评", "判断", "依据", "代表个股", "净流入", "净流出",
        "申购日期", "发行价", "所属行业", "异动原因", "Claw", "锐评",
        "highlight", "concerns", "verdict", "title", "summary",
    })

    def __init__(self, items: list[Item] | None = None):
        self._items = items or []

    def check(self, text: str, items: list[Item]) -> GroundingResult:
        source_items = items or self._items
        source_text = " ".join(
            f"{item.title} {item.raw_text}" for item in source_items
        ).lower()

        entities: set[str] = set()
        for m in self._ENTITY_RE.finditer(text):
            entity = (m.group(1) or m.group(2) or m.group(3) or "").strip()
            if entity and len(entity) >= 2:
                entities.add(entity)

        issues: list[GroundingIssue] = []
        check_entities = entities - self._SKIP_LABELS
        for entity in check_entities:
            e_lower = entity.lower()
            if len(e_lower) <= 4:
                continue
            found = e_lower in source_text
            if not found:
                tokens = re.split(r"[\s\-_·/]+", e_lower)
                found = any(t in source_text for t in tokens if len(t) >= 3)
            if not found:
                issues.append(GroundingIssue(
                    checker=self.name,
                    severity="info",
                    message=f"Entity not found in sources: {entity}",
                    span=entity,
                ))

        total = len(check_entities) or 1
        score = max(1.0 - len(issues) / total, 0.0)
        return GroundingResult(passed=score >= 0.15, score=score, issues=issues)
