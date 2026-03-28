"""Assemble node — combines checked sections into a complete Brief object."""

from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel

from clawcat.llm import get_instructor_client, get_model, get_max_retries
from clawcat.schema.brief import Brief, BriefMetadata, BriefSection, TimeRange
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = """\
根据以下报告各章节内容，撰写一段简明的全文摘要（2-3 句话），提炼最重要的结论。
使用中文撰写，语言精炼、观点明确。

各章节概要：
{sections_overview}
"""


class ExecutiveSummary(BaseModel):
    summary: str


def assemble_node(state: PipelineState) -> dict:
    """Assemble all checked sections into a Brief."""
    task = state.get("task_config")
    sections = state.get("checked_sections", [])

    if not task or not sections:
        return {"error": "No sections to assemble"}

    sections_overview = "\n".join(
        f"- {s.heading}: {s.prose[:150]}..." if s.prose else f"- {s.heading}"
        for s in sections
    )

    client = get_instructor_client()

    exec_summary = client.chat.completions.create(
        model=get_model(),
        response_model=ExecutiveSummary,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM.format(
                sections_overview=sections_overview,
            )},
            {"role": "user", "content": "Write the executive summary."},
        ],
        max_retries=get_max_retries(),
    )

    now = datetime.now()
    brief = Brief(
        report_type=task.period,
        title=f"{task.topic} {'日报' if task.period == 'daily' else '周报'}",
        issue_label=now.strftime("%Y-%m-%d"),
        time_range=TimeRange(
            user_requested=f"{task.since} ~ {task.until}",
            resolved_start=task.since,
            resolved_end=task.until,
            report_generated=now.isoformat(),
        ),
        executive_summary=exec_summary.summary,
        sections=sections,
        metadata=BriefMetadata(
            llm_model=get_model(),
            sources_used=[s.source_name for s in task.selected_sources],
            items_fetched=len(state.get("raw_items", [])),
            items_selected=len(state.get("filtered_items", [])),
        ),
    )

    logger.info("Assembled brief: %s (%d sections)", brief.title, len(brief.sections))
    return {"brief": brief}
