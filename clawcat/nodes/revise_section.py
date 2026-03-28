"""Revise node — rewrites sections that failed grounding checks."""

from __future__ import annotations

import logging

from clawcat.llm import get_instructor_client, get_model, get_max_retries
from clawcat.schema.brief import BriefSection
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)

REVISE_SYSTEM = """\
以下报告章节未通过质量检查，请修正后重写：
- 删除无法从源数据验证的日期/数字
- 确保所有提到的实体都出现在源素材中
- 保持原有结构（heading、section_type、items 格式）不变
- 与报告整体保持一致性
- 使用中文撰写

原始章节（JSON）：
{section_json}

检查发现的问题：
{issues}
"""


def revise_node(state: PipelineState) -> dict:
    """Revise sections that failed grounding."""
    sections = state.get("checked_sections", [])
    retry_indices = state.get("retry_sections", [])

    if not retry_indices:
        return {"draft_sections": sections}

    client = get_instructor_client()

    revised = list(sections)
    for idx in retry_indices:
        if idx >= len(revised):
            continue

        section = revised[idx]
        result = client.chat.completions.create(
            model=get_model(),
            response_model=BriefSection,
            messages=[
                {"role": "system", "content": REVISE_SYSTEM.format(
                    section_json=section.model_dump_json(),
                    issues="Grounding check failures — verify all facts against sources",
                )},
                {"role": "user", "content": f"Revise section: {section.heading}"},
            ],
            max_retries=get_max_retries(),
        )

        result.section_type = section.section_type
        revised[idx] = result
        logger.info("Revised section %d: %s", idx, section.heading)

    return {"draft_sections": revised}
