"""Wall Street CN (华尔街见闻) adapter — Chinese financial news."""

from __future__ import annotations

from datetime import datetime

from clawcat.adapters.base import filter_by_time, make_result, new_client
from clawcat.schema.item import FetchResult, Item


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    config = config or {}
    max_items = config.get("max_items", 20)
    items: list[Item] = []

    async with new_client() as client:
        try:
            resp = await client.get(
                "https://api-one-wscn.awtmt.com/apiv1/content/lives",
                params={"channel": "global-channel", "limit": str(max_items)},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for item_data in data.get("data", {}).get("items", []):
                    title = item_data.get("title", "")
                    content = item_data.get("content_text", "")
                    if not title and content:
                        title = content[:60]
                    if not title:
                        continue
                    pub_ts = item_data.get("display_time", 0)
                    pub_at = datetime.fromtimestamp(pub_ts).isoformat() if pub_ts else ""
                    uri = item_data.get("uri", "")
                    url = f"https://wallstreetcn.com/live/{uri}" if uri else ""
                    items.append(Item(
                        title=title,
                        url=url,
                        source="wallstreetcn",
                        raw_text=content[:300] if content else "",
                        published_at=pub_at,
                        meta={"sub_source": "华尔街见闻"},
                    ))
        except Exception:
            pass

    filtered = filter_by_time(items, since, until)
    return make_result("wallstreetcn", filtered)
