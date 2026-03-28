"""ClawCat LangGraph — the full pipeline as a StateGraph.

Architecture:
  Planner → Fetch → Dedup → Select
  → [Send fan-out] Summarize batches (parallel)
  → Plan
  → [Send fan-out] Write sections (parallel) → Gather
  → Check → Assemble → FinalCheck → Render → Save
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from clawcat.state import PipelineState


def _check_error(state: PipelineState) -> str:
    """Short-circuit to END if an error occurred."""
    if state.get("error"):
        return "end"
    return "continue"


def _fan_out_summarize(state: PipelineState) -> list[Send]:
    """Router: split selected items into batches → parallel summarize nodes."""
    from clawcat.nodes.summarize import BATCH_SIZE, get_selected_items

    items = get_selected_items(state)
    if not items:
        return [Send("summarize_batch", {"filtered_items": []})]

    batches = [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    return [
        Send("summarize_batch", {"filtered_items": batch})
        for batch in batches
    ]


def _fan_out_write(state: PipelineState) -> list[Send]:
    """Router: create one Send per outline section → parallel write nodes."""
    outline = state.get("outline", [])
    if not outline:
        return [Send("write_one_section", {
            "task_config": state.get("task_config"),
            "outline": [],
            "summaries": [],
            "_section_idx": 0,
        })]

    return [
        Send("write_one_section", {
            "task_config": state.get("task_config"),
            "outline": outline,
            "summaries": state.get("summaries", []),
            "_section_idx": i,
        })
        for i in range(len(outline))
    ]


def _should_retry(state: PipelineState) -> str:
    verdict = state.get("gate_verdict", "pass")
    if verdict == "retry":
        return "revise"
    if verdict == "block":
        return "end"
    if verdict == "degrade":
        return "degrade"
    return "render"


def build_graph() -> StateGraph:
    """Construct the full ClawCat pipeline graph."""
    from clawcat.nodes.planner import planner_node
    from clawcat.nodes.fetch import fetch_node
    from clawcat.nodes.dedup import dedup_node
    from clawcat.nodes.select import select_node
    from clawcat.nodes.summarize import summarize_batch_node
    from clawcat.nodes.plan import plan_node
    from clawcat.nodes.write_section import write_one_section_node
    from clawcat.nodes.gather_sections import gather_sections_node
    from clawcat.nodes.check_section import check_sections_node
    from clawcat.nodes.revise_section import revise_node
    from clawcat.nodes.assemble import assemble_node
    from clawcat.nodes.final_check import final_check_node
    from clawcat.nodes.degrade import degrade_node
    from clawcat.nodes.render import render_node
    from clawcat.nodes.save import save_node

    g = StateGraph(PipelineState)

    g.add_node("planner", planner_node)
    g.add_node("fetch", fetch_node)
    g.add_node("dedup", dedup_node)
    g.add_node("select", select_node)
    g.add_node("summarize_batch", summarize_batch_node)
    g.add_node("plan", plan_node)
    g.add_node("write_one_section", write_one_section_node)
    g.add_node("gather_sections", gather_sections_node)
    g.add_node("check", check_sections_node)
    g.add_node("assemble", assemble_node)
    g.add_node("final_check", final_check_node)
    g.add_node("revise", revise_node)
    g.add_node("degrade", degrade_node)
    g.add_node("render", render_node)
    g.add_node("save", save_node)

    g.set_entry_point("planner")

    g.add_conditional_edges("planner", _check_error, {
        "end": END,
        "continue": "fetch",
    })

    g.add_edge("fetch", "dedup")
    g.add_edge("dedup", "select")

    # Fan-out: select → parallel summarize batches → fan-in → plan
    g.add_conditional_edges("select", _fan_out_summarize)
    g.add_edge("summarize_batch", "plan")

    # Fan-out: plan → parallel write sections → fan-in → gather → check
    g.add_conditional_edges("plan", _fan_out_write)
    g.add_edge("write_one_section", "gather_sections")
    g.add_edge("gather_sections", "check")

    g.add_edge("check", "assemble")
    g.add_edge("assemble", "final_check")

    g.add_conditional_edges("final_check", _should_retry, {
        "render": "render",
        "revise": "revise",
        "degrade": "degrade",
        "end": END,
    })

    g.add_edge("revise", "check")
    g.add_edge("degrade", "render")
    g.add_edge("render", "save")
    g.add_edge("save", END)

    return g


def compile_graph():
    """Build and compile the graph, ready for .invoke() or .stream()."""
    return build_graph().compile()
