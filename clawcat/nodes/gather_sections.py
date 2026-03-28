"""Gather node — collects parallel write results and sorts by outline order."""

from __future__ import annotations

import logging

from clawcat.state import PipelineState

logger = logging.getLogger(__name__)


def gather_sections_node(state: PipelineState) -> dict:
    """Fan-in: sort parallel sections to match outline order, then set draft_sections."""
    sections = list(state.get("_parallel_sections", []))
    outline = state.get("outline", [])

    heading_order = {plan.heading: i for i, plan in enumerate(outline)}
    sections.sort(key=lambda s: heading_order.get(s.heading, 999))

    logger.info("Gathered %d sections in outline order", len(sections))
    return {"draft_sections": sections}
