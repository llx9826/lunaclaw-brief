"""Generic RSS/Atom adapter — powered by feedparser."""

from __future__ import annotations

from datetime import datetime
from time import mktime

import feedparser

from clawcat.adapters.base import filter_by_time, make_result
from clawcat.schema.item import FetchResult, Item

DEFAULT_FEEDS = [
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "label": "Ars Technica"},
    {"url": "https://techcrunch.com/feed/", "label": "TechCrunch"},
    {"url": "https://www.theverge.com/rss/index.xml", "label": "The Verge"},
]


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    import asyncio

    config = config or {}
    feeds = config.get("feeds", DEFAULT_FEEDS)
    max_per_feed = config.get("max_per_feed", 10)
    items: list[Item] = []
    seen_urls: set[str] = set()

    for feed_cfg in feeds:
        url = feed_cfg.get("url", "")
        label = feed_cfg.get("label", url[:40])
        if not url:
            continue
        try:
            parsed = await asyncio.to_thread(feedparser.parse, url)
            for entry in parsed.entries[:max_per_feed]:
                link = entry.get("link", "")
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                pub_at = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_at = datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat()
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_at = datetime.fromtimestamp(mktime(entry.updated_parsed)).isoformat()

                summary = entry.get("summary", "")
                if "<" in summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary)

                items.append(Item(
                    title=entry.get("title", ""),
                    url=link,
                    source="rss",
                    raw_text=summary[:400],
                    published_at=pub_at,
                    meta={"sub_source": label},
                ))
        except Exception:
            continue

    filtered = filter_by_time(items, since, until)
    return make_result("rss", filtered)
