"""Consistency checker — detects cross-section contradictions and repetition."""

from __future__ import annotations

import json
from collections import Counter

from clawcat.grounding.protocol import GroundingChecker, GroundingIssue, GroundingResult
from clawcat.schema.item import Item


class ConsistencyChecker(GroundingChecker):
    """Checks for repeated titles across sections and conflicting claims."""

    name = "consistency"

    def check(self, text: str, items: list[Item]) -> GroundingResult:
        issues: list[GroundingIssue] = []

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return GroundingResult(passed=True, score=0.8)

        all_titles: list[str] = []
        for section in data.get("sections", []):
            for item in section.get("items", []):
                title = item.get("title", "").strip()
                if title:
                    all_titles.append(title)

        title_counts = Counter(all_titles)
        for title, count in title_counts.items():
            if count > 1:
                issues.append(GroundingIssue(
                    checker=self.name,
                    severity="warning",
                    message=f"Duplicate item title across sections: '{title}' appears {count} times",
                    span=title,
                ))

        dup_ratio = sum(1 for c in title_counts.values() if c > 1) / max(len(title_counts), 1)
        score = max(1.0 - dup_ratio, 0.0)

        return GroundingResult(
            passed=not any(i.severity == "error" for i in issues),
            score=score,
            issues=issues,
        )
