"""Select node — LLM-driven material selection.

Uses a compact prompt to minimize token usage and latency.
"""

from __future__ import annotations

import logging

from clawcat.llm import get_instructor_client, get_model, get_max_retries
from clawcat.schema.item import Item
from clawcat.schema.task import SelectedItems, TaskConfig, SelectedItem
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)

SELECT_SYSTEM = """\
你是一位简报编辑。请从候选素材中选出最多 {max_items} 条，用于 {period} {topic} 报告。
时间范围：{since} ~ {until}

选择优先级：主题相关性 > 多样性 > 时效性 > 数据丰富度。

候选素材：
{items_text}

返回素材编号和简短理由（每条不超过 10 个字）。
"""


def _format_items_compact(items: list[Item]) -> str:
    """Compact format: only title + source + date. No raw_text to save tokens."""
    return "\n".join(
        f"[{i}] {item.title} ({item.source}, {item.published_at or '?'})"
        for i, item in enumerate(items)
    )


def select_node(state: PipelineState) -> dict:
    """Select: filtered_items → SelectedItems via LLM."""
    task: TaskConfig | None = state.get("task_config")
    items = state.get("filtered_items", [])

    if not task or not items:
        return {"selected_items": SelectedItems()}

    if len(items) <= task.max_items:
        selections = [
            SelectedItem(item_index=i, reason="auto-included", priority=1)
            for i in range(len(items))
        ]
        return {"selected_items": SelectedItems(selections=selections, total_selected=len(items))}

    client = get_instructor_client()

    result = client.chat.completions.create(
        model=get_model(),
        response_model=SelectedItems,
        messages=[
            {"role": "system", "content": SELECT_SYSTEM.format(
                period=task.period,
                topic=task.topic,
                since=task.since,
                until=task.until,
                max_items=task.max_items,
                items_text=_format_items_compact(items),
            )},
            {"role": "user", "content": f"Select the best {task.max_items} items."},
        ],
        max_retries=get_max_retries(),
    )

    result.total_selected = len(result.selections)
    logger.info("Selected %d items from %d candidates", result.total_selected, len(items))
    return {"selected_items": result}
