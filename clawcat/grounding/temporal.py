"""Temporal grounding — detects date hallucinations and out-of-range references."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from clawcat.grounding.protocol import GroundingChecker, GroundingIssue, GroundingResult
from clawcat.schema.item import Item


class TemporalGrounder(GroundingChecker):
    """Checks that all dates in the generated text fall within the expected range."""

    name = "temporal"

    _DATE_RE = re.compile(r"(\d{4})[年\-/.](\d{1,2})[月\-/.](\d{1,2})[日号]?")

    def __init__(self, since: str = "", until: str = ""):
        self._since = since
        self._until = until

    def check(self, text: str, items: list[Item]) -> GroundingResult:
        issues: list[GroundingIssue] = []
        today = datetime.now()

        since_dt = datetime.fromisoformat(self._since) if self._since else None
        until_dt = datetime.fromisoformat(self._until) if self._until else None

        for m in self._DATE_RE.finditer(text):
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                dt = datetime(y, mo, d)

                if dt > today + timedelta(days=365):
                    issues.append(GroundingIssue(
                        checker=self.name,
                        severity="error",
                        message=f"Future date detected: {m.group(0)}",
                        span=m.group(0),
                    ))

                if since_dt and dt < since_dt - timedelta(days=30):
                    issues.append(GroundingIssue(
                        checker=self.name,
                        severity="warning",
                        message=f"Date before report range: {m.group(0)}",
                        span=m.group(0),
                    ))

            except ValueError:
                issues.append(GroundingIssue(
                    checker=self.name,
                    severity="warning",
                    message=f"Invalid date: {m.group(0)}",
                    span=m.group(0),
                ))

        score = 1.0 - min(len(issues) * 0.2, 1.0)
        return GroundingResult(
            passed=not any(i.severity == "error" for i in issues),
            score=score,
            issues=issues,
        )
