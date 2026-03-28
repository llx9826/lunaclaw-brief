"""Brief schema — the single contract between generation and rendering layers.

LLM outputs structured Brief objects via instructor; the renderer consumes
Brief.model_dump() without any Markdown parsing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClawComment(BaseModel):
    """Claw 锐评 — sharp, opinionated commentary on a news item."""

    highlight: str
    concerns: list[str] = []
    verdict: str


class BriefItem(BaseModel):
    """A single reportable item within a section."""

    title: str
    summary: str
    key_facts: list[str] = []
    verdict: str | None = None              # one-line take, used in non-review sections
    claw_comment: ClawComment | None = None  # full commentary, only in review sections
    sources: list[str] = []
    tags: list[str] = []


class BriefSection(BaseModel):
    """One logical section of the brief (e.g. hero, analysis, items)."""

    heading: str
    section_type: str = "items"
    icon: str = ""
    prose: str = ""
    items: list[BriefItem] = []


class TimeRange(BaseModel):
    """Three-timestamp display: what user asked, what we actually covered, when generated."""

    user_requested: str
    resolved_start: str
    resolved_end: str
    report_generated: str
    coverage_gaps: list[str] = []


class BriefMetadata(BaseModel):
    """Pipeline execution metadata attached to every brief."""

    llm_model: str = ""
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    sources_used: list[str] = []
    items_fetched: int = 0
    items_selected: int = 0
    generation_seconds: float = 0.0


class Brief(BaseModel):
    """Top-level brief — the ONLY object crossing the generation→render boundary."""

    schema_version: str = "1.0"
    report_type: str
    title: str
    issue_label: str
    time_range: TimeRange
    executive_summary: str
    sections: list[BriefSection]
    metadata: BriefMetadata = Field(default_factory=BriefMetadata)
