"""36氪 adapter — 中国科技/创业新闻。

多策略抓取：
  1. 热门排行 API
  2. 搜索 API（按主题关键词搜索）
  3. RSS 回退
"""

from __future__ import annotations

import logging
from datetime import datetime

import feedparser

from clawcat.adapters.base import filter_by_time, make_result, new_client
from clawcat.schema.item import FetchResult, Item

logger = logging.getLogger(__name__)

RSS_URL = "https://36kr.com/feed"
HOT_API = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
SEARCH_API = "https://gateway.36kr.com/api/mis/nav/search/resultV2"


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    import asyncio

    config = config or {}
    max_items = config.get("max_items", 30)
    queries: list[str] = config.get("queries", [])

    seen_urls: set[str] = set()
    items: list[Item] = []

    tasks = [_fetch_hot(max_items)]
    if queries:
        tasks.append(_fetch_search(queries, max_items))
    tasks.append(_fetch_rss(max_items))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.warning("36kr 子任务异常: %s", result)
            continue
        for item in result:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                items.append(item)

    filtered = filter_by_time(items, since, until)
    logger.info("36kr: %d items (去重后 %d, 时间过滤后 %d)", len(items), len(seen_urls), len(filtered))
    return make_result("36kr", filtered)


async def _fetch_hot(max_items: int) -> list[Item]:
    items: list[Item] = []
    try:
        async with new_client() as client:
            resp = await client.get(HOT_API, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            if resp.status_code != 200:
                logger.warning("36kr 热门 API 返回 %d", resp.status_code)
                return []
            data = resp.json()
            hot_list = data.get("data", {}).get("hotRankList", [])
            if not hot_list:
                hot_list = data.get("data", {}).get("itemList", [])
            for article in hot_list[:max_items]:
                item = _parse_api_article(article)
                if item:
                    items.append(item)
    except Exception as e:
        logger.warning("36kr 热门 API 异常: %s", e)
    return items


async def _fetch_search(queries: list[str], max_items: int) -> list[Item]:
    items: list[Item] = []
    try:
        async with new_client() as client:
            for query in queries[:5]:
                try:
                    resp = await client.get(
                        SEARCH_API,
                        params={"keyword": query, "pageSize": str(min(max_items, 15))},
                        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                    )
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    item_list = data.get("data", {}).get("itemList", [])
                    for article in item_list[:max_items]:
                        item = _parse_api_article(article)
                        if item:
                            items.append(item)
                except Exception:
                    continue
    except Exception as e:
        logger.warning("36kr 搜索 API 异常: %s", e)
    return items


async def _fetch_rss(max_items: int) -> list[Item]:
    import asyncio
    items: list[Item] = []
    try:
        parsed = await asyncio.to_thread(feedparser.parse, RSS_URL)
        for entry in parsed.entries[:max_items]:
            pub_at = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                from time import mktime
                pub_at = datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat()

            summary = entry.get("summary", "")
            if "<" in summary:
                import re
                summary = re.sub(r"<[^>]+>", "", summary)

            items.append(Item(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                source="36kr",
                raw_text=summary[:400],
                published_at=pub_at,
                meta={"sub_source": "36氪 RSS"},
            ))
    except Exception as e:
        logger.warning("36kr RSS 回退异常: %s", e)
    return items


def _parse_api_article(article: dict) -> Item | None:
    title = article.get("templateMaterial", {}).get("widgetTitle", "")
    if not title:
        title = article.get("title", "")
    if not title:
        return None
    item_id = article.get("itemId", article.get("id", ""))
    url = f"https://36kr.com/p/{item_id}" if item_id else ""
    summary = article.get("templateMaterial", {}).get("widgetContent", "")
    if not summary:
        summary = article.get("summary", "")
    pub_time = article.get("publishTime", "")
    return Item(
        title=title,
        url=url,
        source="36kr",
        raw_text=summary[:400],
        published_at=pub_time,
        meta={"sub_source": "36氪"},
    )
