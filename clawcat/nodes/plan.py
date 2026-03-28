"""Plan node — generates report outline from summaries.

Takes all summaries + TaskConfig.report_structure and produces a refined
outline that maps items to sections.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from clawcat.llm import get_instructor_client, get_model, get_max_retries
from clawcat.schema.task import SectionPlan
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)

PLAN_SYSTEM = """\
你是一位报告架构师。根据素材摘要和预期报告结构，生成精细化的报告大纲。

每个章节需要指定：
- heading：章节标题（中文）
- section_type：类型，可选 "hero"（焦点）、"analysis"（竞品/深度分析）、"items"（资讯列表）、"strategy"（策略）、"review"（Claw 锐评）
- description：本章节要涵盖的内容
- suggested_item_count：建议包含的条目数量

预期结构（由 Planner 提供）：
{structure}

规则：
- 章节数量控制在 4-8 个
- "hero" 章节突出 1-3 个最重要的事件
- "analysis" 章节用于竞品对比或深度分析，必须横向比较而非单独罗列
- "review" 章节是「Claw 锐评」，提供犀利点评
- 必须包含至少一个 "items" 类型的行业新闻章节，覆盖大厂动态、产品发布等行业新闻
- 每个章节的关注点要清晰、不重叠
- 将素材合理分配到对应章节

主题：{topic}
周期：{period}
"""


class ReportOutline(BaseModel):
    sections: list[SectionPlan]


def plan_node(state: PipelineState) -> dict:
    """Plan step: summaries → report outline."""
    task = state.get("task_config")
    summaries = state.get("summaries", [])

    if not task:
        return {"outline": []}

    structure_text = "\n".join(
        f"- {s.heading} ({s.section_type}): {s.description}"
        for s in (task.report_structure or [])
    ) or "No predefined structure — design one based on the content."

    summaries_text = "\n\n".join(
        f"[{i}] {s.get('title', '')} ({s.get('source', '')}): {s.get('summary', s.get('text', ''))}"
        for i, s in enumerate(summaries)
    )

    client = get_instructor_client()

    outline = client.chat.completions.create(
        model=get_model(),
        response_model=ReportOutline,
        messages=[
            {"role": "system", "content": PLAN_SYSTEM.format(
                structure=structure_text,
                topic=task.topic,
                period=task.period,
            )},
            {"role": "user", "content": f"Summaries:\n{summaries_text}"},
        ],
        max_retries=get_max_retries(),
    )

    logger.info("Planned %d sections", len(outline.sections))
    return {"outline": outline.sections}
