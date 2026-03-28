"""Task schema — Planner Agent output that drives the entire pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SectionPlan(BaseModel):
    """Blueprint for one section the Planner wants in the report."""

    heading: str
    section_type: str = "items"
    description: str = ""
    suggested_item_count: int = 3


class SourceSelection(BaseModel):
    """A single data source selected by the Planner."""

    source_name: str
    reason: str = ""
    config: dict = {}


class SelectedItem(BaseModel):
    """One item chosen by the LLM material-selection step."""

    item_index: int
    reason: str
    priority: int = 1
    suggested_section: str = ""


class SelectedItems(BaseModel):
    """LLM material-selection output — which items to include in the report."""

    selections: list[SelectedItem] = []
    total_selected: int = 0


class TaskConfig(BaseModel):
    """Full task specification produced by the Planner Agent.

    Flows from Planner → Fetch → Filter → Generate as the pipeline's
    authoritative configuration.
    """

    topic: str
    period: str = "daily"
    focus_areas: list[str] = []
    selected_sources: list[SourceSelection] = []
    source_config: dict = {}
    report_structure: list[SectionPlan] = []
    tone: str = "professional"
    target_audience: str = "general"
    since: str = ""
    until: str = ""
    max_items: int = 30
    enable_claw_comment: bool = True
