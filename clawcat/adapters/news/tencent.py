"""Tencent News adapter — Chinese general news."""

from __future__ import annotations

from datetime import datetime

from clawcat.adapters.base import filter_by_time, make_result, new_client
from clawcat.schema.item import FetchResult, Item


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    items: list[Item] = []

    async with new_client() as client:
        try:
            resp = await client.get(
                "https://i.news.qq.com/trpc.qqnews_web.kv_srv.kv_srv_http_proxy"
                "/list?sub_srv_id=24hours&srv_id=pc&offset=0&limit=20&strategy=1&ext={}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for article in data.get("data", {}).get("list", [])[:20]:
                    title = article.get("title", "")
                    if not title:
                        continue
                    url = article.get("url", "")
                    abstract = article.get("abstract", "")
                    pub = article.get("publish_time", "")
                    items.append(Item(
                        title=title,
                        url=url,
                        source="tencent",
                        raw_text=abstract[:300],
                        published_at=pub,
                        meta={"sub_source": "腾讯新闻"},
                    ))
        except Exception:
            pass

    filtered = filter_by_time(items, since, until)
    return make_result("tencent", filtered)
