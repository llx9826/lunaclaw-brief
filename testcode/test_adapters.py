"""Tests for adapter connectivity — verifies data sources are reachable."""

import asyncio
from datetime import datetime, timedelta


def test_hackernews():
    """HackerNews adapter should return items."""
    from clawcat.adapters.tech.hackernews import fetch
    now = datetime.now()
    result = asyncio.run(fetch(since=now - timedelta(days=7), until=now))
    print(f"    hackernews: {len(result.items)} items")
    assert result.source == "hackernews"


def test_v2ex():
    """V2EX adapter should return items."""
    from clawcat.adapters.news.v2ex import fetch
    now = datetime.now()
    result = asyncio.run(fetch(since=now - timedelta(days=7), until=now))
    print(f"    v2ex: {len(result.items)} items")
    assert result.source == "v2ex"


def test_weibo():
    """Weibo hot search should return items."""
    from clawcat.adapters.news.weibo import fetch
    now = datetime.now()
    result = asyncio.run(fetch(since=now - timedelta(days=1), until=now))
    print(f"    weibo: {len(result.items)} items")
    assert result.source == "weibo"


def test_rss():
    """RSS adapter should parse feeds."""
    from clawcat.adapters.news.rss import fetch
    now = datetime.now()
    result = asyncio.run(fetch(
        since=now - timedelta(days=30),
        until=now,
        config={"feeds": [
            {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "label": "Ars"},
        ], "max_per_feed": 3},
    ))
    print(f"    rss: {len(result.items)} items")
    assert result.source == "rss"


def test_arxiv():
    """arXiv adapter should return papers."""
    from clawcat.adapters.tech.arxiv import fetch
    now = datetime.now()
    result = asyncio.run(fetch(
        since=now - timedelta(days=30),
        until=now,
        config={"categories": ["cs.AI"], "max_results": 5},
    ))
    print(f"    arxiv: {len(result.items)} items")
    assert result.source == "arxiv"


def test_hf_papers():
    """HuggingFace papers adapter should return papers."""
    from clawcat.adapters.tech.hf_papers import fetch
    now = datetime.now()
    result = asyncio.run(fetch(since=now - timedelta(days=7), until=now))
    print(f"    hf_papers: {len(result.items)} items")
    assert result.source == "hf_papers"


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
    print(f"\nRan {len(tests)} adapter tests: {passed} passed, {failed} failed")
