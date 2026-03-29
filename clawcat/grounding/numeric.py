"""Numeric grounding — verifies numeric claims against source data or fact table."""

from __future__ import annotations

import re

from clawcat.grounding.protocol import GroundingChecker, GroundingIssue, GroundingResult
from clawcat.schema.item import Item


def _extract_num_core(value: str) -> list[str]:
    cores: list[str] = []
    for m in re.finditer(r"[\d,.]+", value):
        raw = m.group(0).replace(",", "").rstrip(".")
        if raw:
            cores.append(raw)
    return cores


class NumericGrounder(GroundingChecker):
    """Verifies numeric claims against source text or a fact table."""

    name = "numeric"

    _NUM_RE = re.compile(
        r"(?:[\$¥€£])\s*[\d,.]+[万亿BMKT]?|"
        r"[+-]?[\d,.]+\s*%|"
        r"[+-]?[\d,.]+\s*(?:亿|万|billion|million|trillion)|"
        r"[\d,]+\.[\d]+(?:点|元)"
    )

    def __init__(self, fact_table=None):
        self._fact_table = fact_table

    def check(self, text: str, items: list[Item]) -> GroundingResult:
        report_nums = {m.group(0).strip() for m in self._NUM_RE.finditer(text)}

        if not report_nums:
            return GroundingResult(passed=True, score=1.0)

        if self._fact_table is not None and hasattr(self._fact_table, "facts"):
            return self._check_against_facts(report_nums)

        return self._check_against_sources(report_nums, items)

    def _check_against_facts(self, report_nums: set[str]) -> GroundingResult:
        fact_values: set[str] = set()
        for f in self._fact_table.facts:
            fact_values.add(f.value)
            for token in _extract_num_core(f.value):
                fact_values.add(token)

        issues: list[GroundingIssue] = []
        grounded = 0

        for num in report_nums:
            core = _extract_num_core(num)
            if any(c in fact_values for c in core):
                grounded += 1
            else:
                issues.append(GroundingIssue(
                    checker=self.name,
                    severity="warning",
                    message=f"Numeric claim not in Fact Table: {num}",
                    span=num,
                ))

        total = len(report_nums)
        score = grounded / total if total else 1.0
        return GroundingResult(passed=score >= 0.3, score=score, issues=issues)

    def _check_against_sources(
        self, report_nums: set[str], items: list[Item],
    ) -> GroundingResult:
        source_text = " ".join(f"{item.title} {item.raw_text}" for item in items)
        source_nums = {m.group(0).strip() for m in self._NUM_RE.finditer(source_text)}
        source_cores = set()
        for sn in source_nums:
            source_cores.update(_extract_num_core(sn))

        issues: list[GroundingIssue] = []
        for num in report_nums:
            cores = _extract_num_core(num)
            if any(c in source_cores for c in cores):
                continue
            if num in source_nums:
                continue
            issues.append(GroundingIssue(
                checker=self.name,
                severity="warning",
                message=f"数值 {num} 在素材中找不到来源，可能为 LLM 编造",
                span=num,
            ))

        total = len(report_nums) or 1
        grounded = total - len(issues)
        score = grounded / total
        return GroundingResult(passed=score >= 0.5, score=score, issues=issues)
