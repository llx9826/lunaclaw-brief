"""Summarize-batch node — processes ONE batch of items.

Called in parallel via LangGraph Send fan-out from the router in graph.py.
Each batch writes to `summaries` (append reducer) for automatic fan-in.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from clawcat.llm import get_instructor_client, get_model, get_max_retries
from clawcat.schema.item import Item
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)

BATCH_SIZE = 5

SUMMARIZE_SYSTEM = """\
你是一位行业分析师。请用 2-3 句话摘要每条素材，并提取关键数值。

关注维度（摘要必须紧扣）：
{focus_areas}

摘要要求：
- 第一句说清「发生了什么」+ 关键数据
- 第二句说清「为什么重要」或「对谁有影响」
- 如果素材与关注维度无关，摘要开头标注「[边缘]」

key_facts 要求（极其重要）：
- 提取素材中所有关键数值，格式为 "指标名: 数值"
- 例如："上证指数: 3913.42点"、"涨幅: +2.3%"、"融资额: 5亿美元"
- 这些数值将作为后续写作的唯一事实依据，必须精确照搬原文数字

返回 JSON 数组，每条素材一个摘要。
"""


class ItemSummary(BaseModel):
    title: str = ""
    summary: str = ""
    key_facts: list[str] = []


class BatchSummary(BaseModel):
    summaries: list[ItemSummary]


def get_selected_items(state: PipelineState) -> list[Item]:
    """Resolve selected items from indices."""
    items = state.get("filtered_items", [])
    selected = state.get("selected_items")
    if not selected or not selected.selections:
        return items
    indices = {s.item_index for s in selected.selections if 0 <= s.item_index < len(items)}
    return [items[i] for i in sorted(indices)]


def summarize_batch_node(state: PipelineState) -> dict:
    """Summarize a single batch of items (called in parallel via Send)."""
    items: list[Item] = state.get("filtered_items", [])
    task = state.get("task_config")

    if not items:
        return {"summaries": []}

    focus_areas = task.focus_areas if task and task.focus_areas else []
    focus_text = "\n".join(f"- {f}" for f in focus_areas) if focus_areas else "- 与主题高度相关的内容"

    client = get_instructor_client()

    items_text = "\n\n".join(
        f"[{i}] {it.title} ({it.source})\n{it.raw_text[:300]}"
        for i, it in enumerate(items)
    )

    result = client.chat.completions.create(
        model=get_model(),
        response_model=BatchSummary,
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM.format(focus_areas=focus_text)},
            {"role": "user", "content": items_text},
        ],
        max_retries=get_max_retries(),
    )

    out: list[dict] = []
    for s, item in zip(result.summaries, items):
        d = s.model_dump()
        d.setdefault("title", item.title)
        d.setdefault("source", item.source)
        d.setdefault("url", item.url)
        d.setdefault("published_at", item.published_at or "")
        out.append(d)

    logger.info("Summarized batch of %d items", len(items))
    return {"summaries": out}
