"""Write-one-section node — generates BriefSection for a single outline entry.

Called in parallel via LangGraph Send fan-out from the router in graph.py.
Each call writes to `_parallel_sections` (append reducer) for automatic fan-in.
"""

from __future__ import annotations

import logging

from clawcat.llm import get_instructor_client, get_model, get_max_retries
from clawcat.prompts.writer import CLAW_COMMENT_INSTRUCTION, VERDICT_INSTRUCTION, WRITE_SECTION_SYSTEM
from clawcat.schema.brief import BriefSection
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)


def write_one_section_node(state: PipelineState) -> dict:
    """Write ONE section (called in parallel via Send)."""
    task = state.get("task_config")
    outline = state.get("outline", [])
    summaries = state.get("summaries", [])
    idx = state.get("_section_idx", 0)

    if not task or idx >= len(outline):
        return {"_parallel_sections": []}

    plan = outline[idx]
    client = get_instructor_client()

    summaries_text = "\n".join(
        f"- {s.get('title', '')}: {s.get('summary', s.get('text', ''))}"
        for s in summaries
    )

    if plan.section_type == "review" and task.enable_claw_comment:
        section_instruction = CLAW_COMMENT_INSTRUCTION
    else:
        section_instruction = VERDICT_INSTRUCTION

    section = client.chat.completions.create(
        model=get_model(),
        response_model=BriefSection,
        messages=[
            {"role": "system", "content": WRITE_SECTION_SYSTEM.format(
                period=task.period,
                topic=task.topic,
                heading=plan.heading,
                section_type=plan.section_type,
                description=plan.description,
                item_count=plan.suggested_item_count,
                since=task.since,
                until=task.until,
                claw_comment_instruction=section_instruction,
                previous_context="(sections are written in parallel)",
                summaries_text=summaries_text,
            )},
            {"role": "user", "content": f"Write section: {plan.heading}"},
        ],
        max_retries=get_max_retries(),
    )

    section.section_type = plan.section_type
    logger.info("Wrote section: %s", plan.heading)
    return {"_parallel_sections": [section]}
