"""Node-level isolation tests — mock data, no LLM calls, fast (seconds).

Tests the input/output contracts between pipeline nodes.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from clawcat.schema.item import Item
from clawcat.schema.brief import BriefSection, BriefItem
from clawcat.schema.task import TaskConfig, SectionPlan
from clawcat.nodes.dedup import dedup_node
from clawcat.nodes.gather_sections import gather_sections_node


def test_dedup_removes_duplicate_items(mock_items, mock_task_config, monkeypatch):
    """Items with the same item_id should be deduplicated."""
    monkeypatch.setattr("clawcat.nodes.dedup._load_seen_ids", lambda: set())

    dup = mock_items[0].model_copy()
    items_with_dup = mock_items + [dup]
    assert len(items_with_dup) == 4

    state = {
        "task_config": mock_task_config,
        "raw_items": items_with_dup,
    }
    result = dedup_node(state)
    filtered = result["filtered_items"]

    assert len(filtered) < len(items_with_dup), "Dedup didn't reduce items"
    ids = [i.item_id for i in filtered]
    assert len(ids) == len(set(ids)), "Duplicate item_ids remain after dedup"


def test_dedup_filters_out_of_range_items(monkeypatch):
    """Items outside the time range should be filtered out."""
    monkeypatch.setattr("clawcat.nodes.dedup._load_seen_ids", lambda: set())

    now = datetime.now()
    task = TaskConfig(
        topic="test",
        since=(now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00"),
        until=(now + timedelta(hours=1)).isoformat(),
    )
    old_item = Item(
        title="Ancient News dedup test",
        source="test_dedup",
        raw_text="Very old news",
        published_at=(now - timedelta(days=365)).isoformat(),
    )
    recent_item = Item(
        title="Fresh News dedup test",
        source="test_dedup",
        raw_text="Today's news",
        published_at=(now - timedelta(hours=2)).isoformat(),
    )
    state = {
        "task_config": task,
        "raw_items": [old_item, recent_item],
    }
    result = dedup_node(state)
    filtered = result["filtered_items"]

    titles = [i.title for i in filtered]
    assert "Ancient News dedup test" not in titles, "Old item was not filtered out"
    assert "Fresh News dedup test" in titles, "Recent item was wrongly filtered"


def test_dedup_empty_input(mock_task_config, monkeypatch):
    """Empty raw_items should produce empty filtered_items."""
    monkeypatch.setattr("clawcat.nodes.dedup._load_seen_ids", lambda: set())
    state = {"task_config": mock_task_config, "raw_items": []}
    result = dedup_node(state)
    assert result["filtered_items"] == []


def test_gather_sorts_by_outline_order():
    """Gather node should sort parallel sections to match outline order."""
    outline = [
        SectionPlan(heading="A 章节"),
        SectionPlan(heading="B 章节"),
        SectionPlan(heading="C 章节"),
    ]
    sections = [
        BriefSection(heading="C 章节", items=[BriefItem(title="c", summary="c")]),
        BriefSection(heading="A 章节", items=[BriefItem(title="a", summary="a")]),
        BriefSection(heading="B 章节", items=[BriefItem(title="b", summary="b")]),
    ]
    state = {"_parallel_sections": sections, "outline": outline}
    result = gather_sections_node(state)

    headings = [s.heading for s in result["draft_sections"]]
    assert headings == ["A 章节", "B 章节", "C 章节"]


def test_gather_empty_sections():
    """Gather with no sections should produce an empty list."""
    state = {"_parallel_sections": [], "outline": []}
    result = gather_sections_node(state)
    assert result["draft_sections"] == []


def test_render_node_produces_html(mock_brief, tmp_path, monkeypatch):
    """Render node should produce HTML and JSON files."""
    from clawcat.nodes.render import render_node

    class FakeSettings:
        output_dir = str(tmp_path)
        template_dir = "clawcat/templates"
        static_dir = "clawcat/static"
        class brand:
            full_name = "ClawCat Brief"
            tagline = "AI-Powered"
            author = "test"

    monkeypatch.setattr("clawcat.nodes.render.get_settings", lambda: FakeSettings())

    state = {"brief": mock_brief}
    result = render_node(state)

    assert "error" not in result or not result.get("error"), f"Render error: {result.get('error')}"

    html_path = result.get("html_path", "")
    json_path = result.get("json_path", "")
    assert html_path and Path(html_path).exists(), "HTML file not created"
    assert json_path and Path(json_path).exists(), "JSON file not created"

    html_content = Path(html_path).read_text(encoding="utf-8")
    assert mock_brief.title in html_content

    json_content = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert json_content["title"] == mock_brief.title
    assert len(json_content["sections"]) == len(mock_brief.sections)


def test_item_auto_generates_id():
    """Item should auto-generate item_id from title+source+url."""
    item = Item(title="Test", source="src", url="http://example.com")
    assert item.item_id, "item_id was not auto-generated"
    assert len(item.item_id) == 16

    same = Item(title="Test", source="src", url="http://example.com")
    assert item.item_id == same.item_id, "Same input should produce same item_id"

    different = Item(title="Other", source="src", url="http://example.com")
    assert item.item_id != different.item_id


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
