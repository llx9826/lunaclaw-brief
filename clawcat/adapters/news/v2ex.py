"""V2EX adapter — Chinese developer community hot topics."""

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
                "https://www.v2ex.com/api/topics/hot.json",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                for topic in resp.json()[:20]:
                    title = topic.get("title", "")
                    if not title:
                        continue
                    created = topic.get("created", 0)
                    pub_at = datetime.fromtimestamp(created).isoformat() if created else ""
                    items.append(Item(
                        title=title,
                        url=topic.get("url", ""),
                        source="v2ex",
                        raw_text=(topic.get("content", "") or "")[:300],
                        published_at=pub_at,
                        meta={
                            "replies": topic.get("replies", 0),
                            "node": topic.get("node", {}).get("name", ""),
                            "sub_source": "V2EX",
                        },
                    ))
        except Exception:
            pass

    filtered = filter_by_time(items, since, until)
    return make_result("v2ex", filtered)
