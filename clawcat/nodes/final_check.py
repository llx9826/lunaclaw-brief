"""Final check node — full-text consistency + coverage + structure verification.

Produces gate_verdict: pass / retry / degrade / block.
"""

from __future__ import annotations

import logging

from clawcat.grounding.consistency import ConsistencyChecker
from clawcat.grounding.coverage import CoverageChecker
from clawcat.grounding.structure import StructureGrounder
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)


def final_check_node(state: PipelineState) -> dict:
    """Run full-text checks and produce a gate verdict."""
    brief = state.get("brief")
    outline = state.get("outline", [])

    if not brief:
        return {"gate_verdict": "block", "error": "No brief to check"}

    brief_json = brief.model_dump_json()
    items = state.get("filtered_items", [])

    checkers = [
        ConsistencyChecker(),
        CoverageChecker(expected_sections=[s.heading for s in outline]),
        StructureGrounder(),
    ]

    total_score = 0.0
    all_issues: list[str] = []

    for checker in checkers:
        try:
            result = checker.check(brief_json, items)
            total_score += result.score
            all_issues.extend(i.message for i in result.issues)
        except Exception as e:
            logger.warning("Full-text checker %s error: %s", checker.__class__.__name__, e)
            total_score += 0.5

    combined_score = total_score / len(checkers)

    if combined_score >= 0.8 and not any("critical" in i.lower() for i in all_issues):
        verdict = "pass"
    elif combined_score >= 0.5:
        verdict = "degrade"
    elif state.get("retry_sections"):
        verdict = "retry"
    else:
        verdict = "block"

    logger.info(
        "Final check: score=%.2f, verdict=%s, issues=%d",
        combined_score, verdict, len(all_issues),
    )
    return {"gate_verdict": verdict}
