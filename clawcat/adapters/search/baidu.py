"""百度搜索适配器 — 基于 baidusearch 库。

特点：
  - 免 API Key
  - 国内直达，中文搜索质量高
  - 适合抓取国内大厂新闻、产品发布、行业动态

Config（由 Planner 通过 SourceSelection.config 传入）：
  queries        list[str]   搜索关键词列表。必填。
  max_per_query  int         每个 query 最大结果数。默认 10。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from clawcat.adapters.base import filter_by_time, make_result
from clawcat.schema.item import FetchResult, Item

logger = logging.getLogger(__name__)


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    config = config or {}
    queries: list[str] = config.get("queries", [])
    max_per_query: int = config.get("max_per_query", 10)

    if not queries:
        logger.warning("baidu: 没有提供搜索关键词，跳过")
        return make_result("baidu", [])

    items: list[Item] = []
    seen_urls: set[str] = set()

    def _search_sync():
        from baidusearch.baidusearch import search
        results = []
        for query in queries:
            try:
                for r in search(query, num_results=max_per_query):
                    results.append((query, r))
            except Exception as e:
                logger.warning("百度搜索 '%s' 失败: %s", query, e)
        return results

    raw_results = await asyncio.to_thread(_search_sync)

    for query, r in raw_results:
        url = r.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = r.get("title", "")
        abstract = r.get("abstract", "")

        items.append(Item(
            title=title,
            url=url,
            source="baidu",
            raw_text=abstract[:500],
            published_at="",
            meta={
                "sub_source": "百度搜索",
                "search_query": query,
            },
        ))

    filtered = filter_by_time(items, since, until)
    logger.info("baidu: %d 条结果（去重后 %d，时间过滤后 %d）",
                len(raw_results), len(items), len(filtered))
    return make_result("baidu", filtered)
