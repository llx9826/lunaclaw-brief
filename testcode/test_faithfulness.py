"""Numeric faithfulness tests — validates the three-layer defense against data fabrication.

Layer 1: Prompt (data anchoring rules in WRITE_SECTION_SYSTEM)
Layer 2: NumericGrounder (post-write check catches fabricated numbers)
Layer 3: Summarize key_facts (structured fact extraction for validation)
"""

from clawcat.grounding.numeric import NumericGrounder
from clawcat.schema.item import Item


def test_numeric_grounder_catches_fabrication():
    """NumericGrounder MUST block when generated numbers differ from source."""
    items = [
        Item(
            title="上证指数",
            source="akshare",
            raw_text="上证指数收于3913.42点，涨幅1.2%。成交额5234亿元。",
        ),
    ]
    fabricated_text = '{"summary": "上证指数报3398点，涨幅2.8%，成交额6000亿元"}'
    result = NumericGrounder().check(fabricated_text, items)

    assert not result.passed, (
        f"NumericGrounder should have BLOCKED fabricated numbers but passed "
        f"(score={result.score:.2f}, issues={len(result.issues)})"
    )
    assert len(result.issues) > 0


def test_numeric_grounder_passes_correct_data():
    """NumericGrounder should pass when numbers match source data."""
    items = [
        Item(
            title="上证指数",
            source="akshare",
            raw_text="上证指数收于3913.42点，涨幅1.2%。成交额5234亿元。",
        ),
    ]
    correct_text = '{"summary": "上证指数收于3913.42点，涨幅1.2%"}'
    result = NumericGrounder().check(correct_text, items)

    assert result.passed, (
        f"NumericGrounder wrongly blocked correct numbers "
        f"(score={result.score:.2f}, issues={[i.message for i in result.issues]})"
    )


def test_numeric_grounder_empty_report():
    """Report with no numbers should always pass."""
    items = [Item(title="Test", source="test", raw_text="上证指数收于3913点")]
    result = NumericGrounder().check('{"summary": "市场表现平稳"}', items)
    assert result.passed


def test_numeric_grounder_partial_match():
    """Report with some correct and some fabricated numbers."""
    items = [
        Item(
            title="Finance",
            source="akshare",
            raw_text="上证指数3913.42点，深证成指11523.67点，涨幅1.2%。",
        ),
    ]
    mixed_text = '{"summary": "上证指数3913.42点（正确），但深证成指报9999.99点（编造）"}'
    result = NumericGrounder().check(mixed_text, items)
    assert any("9999" in i.span for i in result.issues)


def test_summarize_output_contains_key_facts(mock_summaries):
    """Summarize output should include key_facts for Fact Ledger construction."""
    for s in mock_summaries:
        assert "key_facts" in s, f"Summary for '{s.get('title')}' missing key_facts"
        assert len(s["key_facts"]) > 0, f"Summary for '{s.get('title')}' has empty key_facts"
        for fact in s["key_facts"]:
            assert ":" in fact or "：" in fact, (
                f"key_fact '{fact}' should be in 'label: value' format"
            )


def test_fact_ledger_built_from_key_facts(mock_summaries):
    """Fact Ledger should extract numeric cores from key_facts."""
    import re
    num_re = re.compile(r"[\d,.]+")

    all_facts = [f for s in mock_summaries for f in s.get("key_facts", [])]
    all_nums: set[str] = set()
    for fact in all_facts:
        for m in num_re.finditer(fact):
            raw = m.group().replace(",", "").rstrip(".")
            if raw and len(raw) >= 2:
                all_nums.add(raw)

    assert "3913.42" in all_nums or "3913" in all_nums, "Index value should be in ledger"
    assert "1500" in all_nums, "Revenue value should be in ledger"
    assert "380" in all_nums, "Profit value should be in ledger"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
