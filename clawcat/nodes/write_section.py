"""Write-one-section node — generates BriefSection for a single outline entry.

Called in parallel via LangGraph Send fan-out from the router in graph.py.
Each call writes to `_parallel_sections` (append reducer) for automatic fan-in.

Numeric grounding uses instructor's llm_validator + small model (inspired by VeNRA):
Summarize stage extracts key_facts → llm_validator checks prose against them.
Validation failure → instructor auto-retries the Write call with error context.
"""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import BeforeValidator
from instructor import llm_validator

from clawcat.llm import get_instructor_client, get_model, get_validator_model, get_max_retries
from clawcat.prompts.writer import (
    CLAW_COMMENT_INSTRUCTION, VERDICT_INSTRUCTION,
    WRITE_SECTION_SYSTEM, TONE_DESCRIPTIONS,
)
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

    def _format_summary(s: dict) -> str:
        line = f"- {s.get('title', '')}: {s.get('summary', s.get('text', ''))}"
        facts = s.get("key_facts", [])
        if facts:
            line += f"\n  关键数值：{' | '.join(facts)}"
        return line

    summaries_text = "\n".join(_format_summary(s) for s in summaries)

    if plan.section_type == "review" and task.enable_claw_comment:
        section_instruction = CLAW_COMMENT_INSTRUCTION
    else:
        section_instruction = VERDICT_INSTRUCTION

    tone_desc = TONE_DESCRIPTIONS.get(task.tone, TONE_DESCRIPTIONS["professional"])
    focus_text = "\n".join(f"- {f}" for f in task.focus_areas) if task.focus_areas else "- 与主题高度相关的内容"

    facts_text = "\n".join(
        f"- {fact}" for s in summaries for fact in s.get("key_facts", [])
    )

    ground_check = llm_validator(
        statement=(
            "文本中所有关键数值（指数点位、股价、涨跌幅、金额、百分比）"
            "必须能在以下事实数据中找到来源，不允许凭记忆编造：\n" + (facts_text or "（无数值约束）")
        ),
        client=client,
        model=get_validator_model(),
    )

    class GroundedSection(BriefSection):
        prose: Annotated[str, BeforeValidator(ground_check)] = ""

    section = client.chat.completions.create(
        model=get_model(),
        response_model=GroundedSection,
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
                target_audience=task.target_audience,
                tone_desc=tone_desc,
                focus_areas=focus_text,
                claw_comment_instruction=section_instruction,
                summaries_text=summaries_text,
            )},
            {"role": "user", "content": f"Write section: {plan.heading}"},
        ],
        max_retries=get_max_retries(),
    )

    section.section_type = plan.section_type
    logger.info("Wrote section: %s", plan.heading)
    return {"_parallel_sections": [section]}
