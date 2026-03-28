"""Tests for all Pydantic schema models."""

import json
from datetime import datetime

from clawcat.schema.brief import Brief, BriefItem, BriefMetadata, BriefSection, ClawComment, TimeRange
from clawcat.schema.item import FetchResult, Item
from clawcat.schema.task import SectionPlan, SelectedItem, SelectedItems, SourceSelection, TaskConfig
from clawcat.schema.user import UserProfile


def test_item_auto_id():
    """item_id should be auto-computed from title+source+url."""
    item = Item(title="Test", source="hackernews", url="https://example.com")
    assert item.item_id, "item_id should be auto-generated"
    assert len(item.item_id) == 16

    same = Item(title="Test", source="hackernews", url="https://example.com")
    assert item.item_id == same.item_id, "Same inputs should produce same ID"

    different = Item(title="Other", source="hackernews", url="https://example.com")
    assert item.item_id != different.item_id


def test_item_datetime_iso():
    """published_datetime should parse standard ISO8601."""
    item = Item(title="t", source="s", published_at="2026-03-28T10:30:00")
    dt = item.published_datetime
    assert dt is not None
    assert dt.year == 2026 and dt.month == 3 and dt.day == 28


def test_item_datetime_with_timezone():
    """published_datetime should handle ISO8601 with Z and offsets."""
    item_z = Item(title="t", source="s", published_at="2026-03-28T10:30:00Z")
    assert item_z.published_datetime is not None

    item_offset = Item(title="t", source="s", published_at="2026-03-28T10:30:00+08:00")
    assert item_offset.published_datetime is not None


def test_item_datetime_rss():
    """published_datetime should handle RSS pubDate format."""
    item = Item(title="t", source="s", published_at="Sat, 28 Mar 2026 10:30:00 GMT")
    assert item.published_datetime is not None


def test_item_datetime_none():
    """published_datetime should return None for unparseable dates."""
    item = Item(title="t", source="s", published_at="garbage")
    assert item.published_datetime is None

    item_empty = Item(title="t", source="s")
    assert item_empty.published_datetime is None


def test_brief_roundtrip():
    """Brief should serialize/deserialize cleanly via JSON."""
    brief = Brief(
        report_type="daily",
        title="AI 日报",
        issue_label="2026-03-28",
        time_range=TimeRange(
            user_requested="今天",
            resolved_start="2026-03-28T00:00:00",
            resolved_end="2026-03-28T23:59:59",
            report_generated="2026-03-28T15:00:00",
        ),
        executive_summary="测试摘要",
        sections=[
            BriefSection(
                heading="头条",
                section_type="hero",
                prose="今日要闻",
                items=[
                    BriefItem(
                        title="大新闻",
                        summary="发生了大事",
                        key_facts=["事实1", "事实2"],
                        verdict="一句话短评",
                        sources=["hackernews"],
                        tags=["AI"],
                    )
                ],
            ),
            BriefSection(
                heading="锐评",
                section_type="review",
                prose="深度点评",
                items=[
                    BriefItem(
                        title="锐评事件",
                        summary="深度分析",
                        key_facts=["事实A"],
                        claw_comment=ClawComment(
                            highlight="犀利观点",
                            concerns=["风险1"],
                            verdict="总结判断",
                        ),
                        sources=["36kr"],
                        tags=["评论"],
                    )
                ],
            ),
        ],
    )

    data = brief.model_dump()
    assert data["schema_version"] == "1.0"
    assert len(data["sections"]) == 2
    assert data["sections"][0]["items"][0]["verdict"] == "一句话短评"
    assert data["sections"][0]["items"][0]["claw_comment"] is None
    assert data["sections"][1]["items"][0]["claw_comment"]["highlight"] == "犀利观点"

    restored = Brief.model_validate(data)
    assert restored.title == brief.title

    json_str = brief.model_dump_json()
    from_json = Brief.model_validate_json(json_str)
    assert from_json.executive_summary == "测试摘要"


def test_task_config():
    """TaskConfig should have sensible defaults."""
    config = TaskConfig(topic="AI", period="daily")
    assert config.tone == "professional"
    assert config.max_items == 30
    assert config.enable_claw_comment is True


def test_fetch_result():
    """FetchResult should auto-set fetched_at."""
    result = FetchResult(source="test", items=[])
    assert result.fetched_at, "fetched_at should be auto-set"


def test_user_profile_defaults():
    """UserProfile should have sensible defaults."""
    profile = UserProfile()
    assert profile.user_id == "default"
    assert profile.tone_preference == "professional"


def test_selected_items():
    """SelectedItems should serialize correctly."""
    sel = SelectedItems(
        selections=[
            SelectedItem(item_index=0, reason="important", priority=1),
            SelectedItem(item_index=3, reason="trending", priority=2),
        ],
        total_selected=2,
    )
    data = sel.model_dump()
    assert len(data["selections"]) == 2


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
    print(f"\nRan {len(tests)} tests")
