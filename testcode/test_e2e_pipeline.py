"""End-to-end pipeline test — run the full LangGraph pipeline and validate output.

Usage:
    pytest testcode/test_e2e_pipeline.py -v
    pytest testcode/test_e2e_pipeline.py -v -m slow   # only E2E (needs LLM + network)
"""

import pytest
from pathlib import Path


@pytest.mark.slow
def test_full_pipeline_produces_valid_brief():
    """Input a single sentence → get a complete Brief with all required fields."""
    from clawcat.graph import compile_graph

    graph = compile_graph()
    result = graph.invoke({"user_input": "AI技术今日速递"})

    assert "error" not in result or not result["error"], f"Pipeline error: {result.get('error')}"

    brief = result.get("brief")
    assert brief is not None, "Pipeline did not produce a brief"

    assert brief.title, "Brief title is empty"
    assert brief.report_type in ("daily", "weekly")
    assert brief.executive_summary, "Executive summary is empty"

    assert len(brief.sections) >= 2, f"Too few sections: {len(brief.sections)}"
    for section in brief.sections:
        assert section.heading, "Section heading is empty"
        assert len(section.items) >= 1, f"Section '{section.heading}' has no items"
        for item in section.items:
            assert item.title, "Item title is empty"
            assert item.summary, f"Item '{item.title}' has no summary"

    tr = brief.time_range
    assert tr.resolved_start, "resolved_start missing"
    assert tr.resolved_end, "resolved_end missing"
    assert tr.report_generated, "report_generated missing"

    meta = brief.metadata
    assert meta.items_fetched > 0, "items_fetched is 0"
    assert len(meta.sources_used) > 0, "sources_used is empty"


@pytest.mark.slow
def test_pipeline_generates_output_files():
    """Pipeline should produce HTML and JSON files on disk."""
    from clawcat.graph import compile_graph

    graph = compile_graph()
    result = graph.invoke({"user_input": "开源技术每周概览"})

    html_path = result.get("html_path", "")
    json_path = result.get("json_path", "")

    assert html_path and Path(html_path).exists(), f"HTML not found: {html_path}"
    assert json_path and Path(json_path).exists(), f"JSON not found: {json_path}"

    html_content = Path(html_path).read_text(encoding="utf-8")
    assert "<html" in html_content.lower(), "HTML file doesn't contain <html> tag"
    assert len(html_content) > 500, "HTML file suspiciously small"


@pytest.mark.slow
def test_pipeline_sections_match_report_structure():
    """Sections in the Brief should roughly match the Planner's report_structure."""
    from clawcat.graph import compile_graph

    graph = compile_graph()
    result = graph.invoke({"user_input": "A股市场今日复盘"})

    brief = result.get("brief")
    assert brief is not None

    section_types = [s.section_type for s in brief.sections]
    assert "hero" in section_types, "Missing 'hero' section"
    assert "review" in section_types, "Missing 'review' section"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
