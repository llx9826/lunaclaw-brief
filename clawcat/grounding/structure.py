"""Structure grounding — validates report structure against requirements."""

from __future__ import annotations

import json

from clawcat.grounding.protocol import GroundingChecker, GroundingIssue, GroundingResult
from clawcat.schema.item import Item


class StructureGrounder(GroundingChecker):
    """Validates section count and Claw comment presence in JSON output."""

    name = "structure"

    def check(self, text: str, items: list[Item]) -> GroundingResult:
        issues: list[GroundingIssue] = []

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            data = {}

        sections = data.get("sections", [])

        if len(sections) < 2:
            issues.append(GroundingIssue(
                checker=self.name,
                severity="error",
                message=f"Too few sections: {len(sections)}, expected ≥2",
            ))

        total_items = 0
        claw_count = 0
        for sec in sections:
            sec_items = sec.get("items", [])
            total_items += len(sec_items)
            for item in sec_items:
                if item.get("claw_comment"):
                    claw_count += 1

        review_sections = [s for s in sections if s.get("section_type") == "review"]
        if review_sections:
            review_items = sum(len(s.get("items", [])) for s in review_sections)
            if review_items > 0 and claw_count < review_items:
                issues.append(GroundingIssue(
                    checker=self.name,
                    severity="warning",
                    message=f"Review section: {claw_count}/{review_items} items have claw_comment",
                ))

        section_score = min(len(sections) / 4, 1.0)
        item_score = min(total_items / 5, 1.0) if total_items else 0.5
        score = section_score * 0.6 + item_score * 0.4

        return GroundingResult(
            passed=not any(i.severity == "error" for i in issues),
            score=score,
            issues=issues,
        )
