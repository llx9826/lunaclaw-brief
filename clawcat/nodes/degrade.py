"""Degrade node — replaces unverifiable data and produces a safe-to-publish brief."""

from __future__ import annotations

import logging

from clawcat.state import PipelineState

logger = logging.getLogger(__name__)


def degrade_node(state: PipelineState) -> dict:
    """Strip unverifiable claims from the brief before rendering."""
    brief = state.get("brief")
    if not brief:
        return {"gate_verdict": "block"}

    for section in brief.sections:
        for item in section.items:
            item.key_facts = [
                f for f in item.key_facts
                if not any(w in f for w in ["据传", "未经证实", "unverified"])
            ]

    logger.info("Degraded brief: removed unverifiable claims")
    return {"brief": brief, "gate_verdict": "pass"}
