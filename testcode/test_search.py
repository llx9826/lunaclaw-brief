"""Quick test for search adapters."""
import asyncio
from datetime import datetime, timedelta

import pytest


@pytest.mark.network
@pytest.mark.asyncio
async def test_ddg():
    from clawcat.adapters.search.duckduckgo import fetch
    since = datetime.now() - timedelta(days=7)
    until = datetime.now()
    r = await fetch(since, until, {
        "queries": ["阿里 OCR 开源", "OCR open source model 2026"],
        "max_results": 5,
        "region": "cn-zh",
    })
    print(f"DuckDuckGo: {len(r.items)} items")
    for it in r.items[:5]:
        pub = it.published_at[:16] if it.published_at else "?"
        print(f"  [{pub}] {it.title[:70]}")
        print(f"    {it.url[:90]}")
    print()


@pytest.mark.network
@pytest.mark.asyncio
async def test_baidu():
    from clawcat.adapters.search.baidu import fetch
    since = datetime.now() - timedelta(days=7)
    until = datetime.now()
    r = await fetch(since, until, {
        "queries": ["阿里 OCR 开源", "百度文字识别 2026"],
        "max_per_query": 5,
    })
    print(f"Baidu: {len(r.items)} items")
    for it in r.items[:5]:
        print(f"  {it.title[:70]}")
        print(f"    {it.url[:90]}")
    print()


async def main():
    print("=== DuckDuckGo ===")
    await test_ddg()
    print("=== Baidu ===")
    await test_baidu()


if __name__ == "__main__":
    asyncio.run(main())
