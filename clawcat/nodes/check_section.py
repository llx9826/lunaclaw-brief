"""Check node — runs chapter-level grounding checks on each drafted section.

Chapter-level checkers: temporal, entity, numeric.
Structure and coverage checks happen at full-text level in final_check.
"""

from __future__ import annotations

import logging

from clawcat.schema.brief import BriefSection
from clawcat.schema.item import Item
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)


def check_sections_node(state: PipelineState) -> dict:
    """Check each drafted section against grounding rules."""
    from clawcat.grounding.temporal import TemporalGrounder
    from clawcat.grounding.entity import EntityGrounder
    from clawcat.grounding.numeric import NumericGrounder

    sections = state.get("draft_sections", [])
    items = state.get("filtered_items", [])
    task = state.get("task_config")

    if not sections:
        return {"checked_sections": []}

    hard_checkers = [
        TemporalGrounder(since=task.since if task else "", until=task.until if task else ""),
        NumericGrounder(),
    ]
    soft_checkers = [
        EntityGrounder(items=items),
    ]

    checked: list[BriefSection] = []
    retry_indices: list[int] = []

    for i, section in enumerate(sections):
        section_text = section.model_dump_json()
        hard_passed = True

        for checker in hard_checkers:
            try:
                result = checker.check(section_text, items)
                if not result.passed:
                    logger.warning(
                        "Section %d (%s) failed %s: score=%.2f, issues=%d",
                        i, section.heading, checker.__class__.__name__,
                        result.score, len(result.issues),
                    )
                    hard_passed = False
            except Exception as e:
                logger.warning("Checker %s error on section %d: %s",
                               checker.__class__.__name__, i, e)

        for checker in soft_checkers:
            try:
                result = checker.check(section_text, items)
                if not result.passed:
                    logger.info(
                        "Section %d (%s) soft-warn %s: score=%.2f, issues=%d",
                        i, section.heading, checker.__class__.__name__,
                        result.score, len(result.issues),
                    )
            except Exception:
                pass

        if not hard_passed:
            retry_indices.append(i)
        checked.append(section)

    logger.info("Checked %d sections: %d passed, %d need retry",
                len(sections), len(sections) - len(retry_indices), len(retry_indices))
    return {
        "checked_sections": checked,
        "retry_sections": retry_indices,
    }
