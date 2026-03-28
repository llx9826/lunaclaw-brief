"""Coverage checker — ensures all planned sections are present in the report."""

from __future__ import annotations

import json

from clawcat.grounding.protocol import GroundingChecker, GroundingIssue, GroundingResult
from clawcat.schema.item import Item


class CoverageChecker(GroundingChecker):
    """Validates that the final brief covers all sections from the outline."""

    name = "coverage"

    def __init__(self, expected_sections: list[str] | None = None):
        self._expected = expected_sections or []

    def check(self, text: str, items: list[Item]) -> GroundingResult:
        if not self._expected:
            return GroundingResult(passed=True, score=1.0)

        issues: list[GroundingIssue] = []

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return GroundingResult(passed=False, score=0.0, issues=[
                GroundingIssue(checker=self.name, severity="error", message="Cannot parse brief JSON"),
            ])

        actual_headings = {
            s.get("heading", "").strip().lower()
            for s in data.get("sections", [])
        }

        for expected in self._expected:
            if expected.strip().lower() not in actual_headings:
                issues.append(GroundingIssue(
                    checker=self.name,
                    severity="warning",
                    message=f"Missing section from outline: '{expected}'",
                    span=expected,
                ))

        covered = len(self._expected) - len(issues)
        score = covered / len(self._expected) if self._expected else 1.0

        return GroundingResult(
            passed=score >= 0.7,
            score=score,
            issues=issues,
        )
