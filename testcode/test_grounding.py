"""Tests for all grounding checkers."""

import json

from clawcat.grounding.temporal import TemporalGrounder
from clawcat.grounding.entity import EntityGrounder
from clawcat.grounding.numeric import NumericGrounder
from clawcat.grounding.structure import StructureGrounder
from clawcat.grounding.consistency import ConsistencyChecker
from clawcat.grounding.coverage import CoverageChecker
from clawcat.schema.item import Item


def _make_items():
    return [
        Item(title="OpenAI发布GPT-5", source="hackernews", url="https://openai.com",
             raw_text="OpenAI today announced GPT-5 with 10x performance improvement. Stock up 15%."),
        Item(title="腾讯Q4财报", source="36kr", url="https://36kr.com/1",
             raw_text="腾讯2026年Q4营收1500亿，同比增长12%。"),
    ]


def test_temporal_pass():
    """Normal dates within range should pass."""
    checker = TemporalGrounder(since="2026-01-01T00:00:00", until="2026-12-31T23:59:59")
    result = checker.check("事件发生在2026年3月28日", _make_items())
    assert result.passed


def test_temporal_future_date():
    """Far future dates should be flagged."""
    checker = TemporalGrounder()
    result = checker.check("预计在2099年1月1日发布", [])
    assert not result.passed
    assert any("Future date" in i.message for i in result.issues)


def test_entity_found():
    """Entities present in source items should pass."""
    checker = EntityGrounder()
    result = checker.check('报告提到了 **OpenAI** 和 **GPT-5**', _make_items())
    assert result.passed


def test_entity_not_found():
    """Fabricated entities should be flagged."""
    checker = EntityGrounder()
    result = checker.check('**FakeCompanyXYZ** 发布了新产品', _make_items())
    assert any("FakeCompanyXYZ" in i.span for i in result.issues)


def test_numeric_in_sources():
    """Numbers present in source text should pass."""
    checker = NumericGrounder()
    result = checker.check("增长了12%，营收1500亿", _make_items())
    assert result.passed
    assert result.score >= 0.5


def test_numeric_not_in_sources():
    """Fabricated numbers should be flagged and blocked (score < 0.5)."""
    checker = NumericGrounder()
    result = checker.check("股价暴涨99.99%，市值达到8888亿", _make_items())
    assert not result.passed, "NumericGrounder must block fabricated numbers"
    assert any("99.99%" in i.span for i in result.issues)


def test_structure_valid_brief():
    """A well-structured brief JSON should pass."""
    brief = {
        "sections": [
            {"heading": "头条", "section_type": "hero", "items": [
                {"title": "a", "claw_comment": {"highlight": "x", "concerns": [], "verdict": "y"}},
            ]},
            {"heading": "分析", "section_type": "analysis", "items": [
                {"title": "b"},
            ]},
            {"heading": "锐评", "section_type": "review", "items": [
                {"title": "c", "claw_comment": {"highlight": "z", "concerns": [], "verdict": "w"}},
            ]},
            {"heading": "策略", "section_type": "strategy", "items": []},
        ]
    }
    checker = StructureGrounder()
    result = checker.check(json.dumps(brief), [])
    assert result.passed


def test_structure_too_few_sections():
    """Brief with only 1 section should fail."""
    brief = {"sections": [{"heading": "only", "items": []}]}
    checker = StructureGrounder()
    result = checker.check(json.dumps(brief), [])
    assert not result.passed


def test_consistency_no_duplicates():
    """Brief without duplicate item titles should pass."""
    brief = {
        "sections": [
            {"items": [{"title": "A"}, {"title": "B"}]},
            {"items": [{"title": "C"}]},
        ]
    }
    checker = ConsistencyChecker()
    result = checker.check(json.dumps(brief), [])
    assert result.passed
    assert result.score == 1.0


def test_consistency_with_duplicates():
    """Duplicate item titles across sections should be flagged."""
    brief = {
        "sections": [
            {"items": [{"title": "Same News"}, {"title": "B"}]},
            {"items": [{"title": "Same News"}]},
        ]
    }
    checker = ConsistencyChecker()
    result = checker.check(json.dumps(brief), [])
    assert any("Duplicate" in i.message for i in result.issues)


def test_coverage_all_present():
    """All expected sections present should pass."""
    brief = {
        "sections": [
            {"heading": "头条"},
            {"heading": "分析"},
        ]
    }
    checker = CoverageChecker(expected_sections=["头条", "分析"])
    result = checker.check(json.dumps(brief), [])
    assert result.passed
    assert result.score == 1.0


def test_coverage_missing():
    """Missing sections should be flagged."""
    brief = {"sections": [{"heading": "头条"}]}
    checker = CoverageChecker(expected_sections=["头条", "分析", "锐评"])
    result = checker.check(json.dumps(brief), [])
    assert result.score < 1.0
    assert any("分析" in i.span for i in result.issues)


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
    print(f"\nRan {len(tests)} tests: {passed} passed, {failed} failed")
