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
你是一位新闻分析师。请用 2-3 句话摘要每条素材，重点关注：
- 发生了什么、为什么重要
- 关键数字或数据
- 影响范围和对象

返回 JSON 数组，每条素材一个摘要。
"""


class BatchSummary(BaseModel):
    summaries: list[dict]


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

    if not items:
        return {"summaries": []}

    client = get_instructor_client()

    items_text = "\n\n".join(
        f"[{i}] {it.title} ({it.source})\n{it.raw_text[:300]}"
        for i, it in enumerate(items)
    )

    result = client.chat.completions.create(
        model=get_model(),
        response_model=BatchSummary,
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM},
            {"role": "user", "content": items_text},
        ],
        max_retries=get_max_retries(),
    )

    for s, item in zip(result.summaries, items):
        s.setdefault("title", item.title)
        s.setdefault("source", item.source)
        s.setdefault("url", item.url)
        s.setdefault("published_at", item.published_at or "")

    logger.info("Summarized batch of %d items", len(items))
    return {"summaries": result.summaries}
