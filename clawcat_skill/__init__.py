"""clawcat_skill — Host-AI Skill mode for ClawCat Brief.

This package provides three tool functions (plan_report, fetch_data,
render_report) that a host AI can call to generate structured briefings
WITHOUT bringing its own LLM.  The host AI is the intelligence layer;
this package handles only I/O (data fetching, dedup, rendering).
"""

__version__ = "1.0.0"

from clawcat_skill.tools import plan_report, fetch_data, render_report

__all__ = ["plan_report", "fetch_data", "render_report"]
