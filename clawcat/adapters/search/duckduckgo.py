"""DuckDuckGo 搜索适配器 — 基于 ddgs 库。

特点：
  - 免 API Key
  - 支持 text() 网页搜索 + news() 新闻搜索（自带日期字段）
  - timelimit 支持时间过滤（d=日/w=周/m=月）
  - 支持代理（国内可配置 proxy）

Config（由 Planner 通过 SourceSelection.config 传入）：
  queries      list[str]   搜索关键词列表。必填。
  max_results  int         每个 query 最大结果数。默认 10。
  region       str         搜索区域，如 "cn-zh"（中文）、"wt-wt"（全球）。默认 "wt-wt"。
  use_news     bool        是否用 news() 代替 text()，新闻搜索有日期。默认 True。
  proxy        str         代理地址，如 "http://127.0.0.1:7890"。默认空。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from clawcat.adapters.base import filter_by_time, make_result
from clawcat.schema.item import FetchResult, Item

logger = logging.getLogger(__name__)

TIMELIMIT_MAP = {"daily": "d", "weekly": "w", "monthly": "m"}


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    config = config or {}
    queries: list[str] = config.get("queries", [])
    max_results: int = config.get("max_results", 10)
    region: str = config.get("region", "wt-wt")
    use_news: bool = config.get("use_news", True)
    proxy: str = config.get("proxy", "")

    if not queries:
        logger.warning("duckduckgo: 没有提供搜索关键词，跳过")
        return make_result("duckduckgo", [])

    days_span = (until - since).days
    if days_span <= 1:
        timelimit = "d"
    elif days_span <= 7:
        timelimit = "w"
    else:
        timelimit = "m"

    items: list[Item] = []
    seen_urls: set[str] = set()

    def _search_sync():
        from ddgs import DDGS
        ddgs = DDGS(proxy=proxy or None, timeout=20)
        results = []
        for query in queries:
            try:
                if use_news:
                    for r in ddgs.news(query, region=region, timelimit=timelimit, max_results=max_results):
                        results.append(("news", query, r))
                else:
                    for r in ddgs.text(query, region=region, timelimit=timelimit, max_results=max_results):
                        results.append(("text", query, r))
            except Exception as e:
                logger.warning("duckduckgo 搜索 '%s' 失败: %s", query, e)
        return results

    raw_results = await asyncio.to_thread(_search_sync)

    for mode, query, r in raw_results:
        url = r.get("url") or r.get("href", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = r.get("title", "")
        body = r.get("body", "") or r.get("excerpt", "")
        source_name = r.get("source", "duckduckgo")
        published = r.get("date", "") if mode == "news" else ""

        items.append(Item(
            title=title,
            url=url,
            source="duckduckgo",
            raw_text=body[:500],
            published_at=published,
            meta={
                "sub_source": source_name,
                "search_query": query,
                "search_mode": mode,
            },
        ))

    filtered = filter_by_time(items, since, until)
    logger.info("duckduckgo: %d 条结果（去重后 %d，时间过滤后 %d）",
                len(raw_results), len(items), len(filtered))
    return make_result("duckduckgo", filtered)
