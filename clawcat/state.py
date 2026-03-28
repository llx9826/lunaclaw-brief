"""Pipeline state — the single TypedDict flowing through every LangGraph node."""

from __future__ import annotations

from typing import Annotated, TypedDict

from clawcat.schema.brief import Brief, BriefSection
from clawcat.schema.item import Item
from clawcat.schema.task import SectionPlan, SelectedItems, TaskConfig


def _merge_lists(a: list, b: list) -> list:
    """Reducer: append new items to existing list (for fan-out gather)."""
    return a + b


class PipelineState(TypedDict, total=False):
    """Mutable state bag passed through the LangGraph pipeline.

    Fields with Annotated[..., _merge_lists] use append semantics
    (needed for parallel fan-out results).
    All other fields use replace semantics (last writer wins).
    """

    # Phase 1: Planning
    user_input: str
    task_config: TaskConfig

    # Phase 2: Fetch & Filter
    raw_items: Annotated[list[Item], _merge_lists]
    filtered_items: list[Item]

    # Phase 3: Selection
    selected_items: SelectedItems

    # Phase 4: Generation (Map-Plan-Write)
    summaries: Annotated[list[dict], _merge_lists]          # fan-out from summarize
    outline: list[SectionPlan]
    _parallel_sections: Annotated[list[BriefSection], _merge_lists]  # fan-out from write
    draft_sections: list[BriefSection]                      # replace: set by gather / revise

    # Phase 5: Check & Assemble
    checked_sections: list[BriefSection]
    brief: Brief

    # Phase 6: Output
    json_path: str
    html_path: str
    pdf_path: str

    # Fan-out control (set by Send routers)
    _section_idx: int

    # Control flow
    retry_sections: list[int]
    gate_verdict: str
    error: str
