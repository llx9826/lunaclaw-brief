"""Hacker News adapter — via Algolia search API.

支持动态 queries 从 Planner config 传入，搜索与主题相关的内容。
"""

from __future__ import annotations

import logging
from datetime import datetime

from clawcat.adapters.base import filter_by_time, make_result, new_client
from clawcat.schema.item import FetchResult, Item

logger = logging.getLogger(__name__)

DEFAULT_QUERIES = [
    "AI OR LLM OR machine learning",
    "startup OR tech industry",
]


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    config = config or {}
    queries = config.get("queries", DEFAULT_QUERIES)
    max_per_query = config.get("max_per_query", 10)
    min_points = config.get("min_points", 3)
    items: list[Item] = []
    seen_urls: set[str] = set()

    async with new_client() as client:
        for query in queries:
            try:
                resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={
                        "query": query,
                        "tags": "story",
                        "numericFilters": f"points>{min_points}",
                    },
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for story in data.get("hits", [])[:max_per_query]:
                    title = story.get("title", "")
                    if not title:
                        continue
                    url = story.get("url") or (
                        f"https://news.ycombinator.com/item?id={story.get('objectID', '')}"
                    )
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    items.append(Item(
                        title=title,
                        url=url,
                        source="hackernews",
                        raw_text="",
                        published_at=story.get("created_at", ""),
                        meta={
                            "points": story.get("points", 0),
                            "comments": story.get("num_comments", 0),
                        },
                    ))
            except Exception:
                continue

    filtered = filter_by_time(items, since, until)
    logger.info("hackernews: %d items (过滤后 %d)", len(items), len(filtered))
    return make_result("hackernews", filtered)
