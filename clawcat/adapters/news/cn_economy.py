"""CN Economy adapter — official Chinese economic news from Eastmoney."""

from __future__ import annotations

import re
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
                "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns",
                params={
                    "columns": "102",
                    "pageSize": "20",
                    "client": "wap",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                news_list = data.get("data", {}).get("list", [])
                if not news_list and isinstance(data.get("data"), list):
                    news_list = data["data"]
                for article in news_list[:20]:
                    title = article.get("title", "")
                    if not title:
                        continue
                    url = article.get("url", "")
                    if not url:
                        art_id = article.get("art_code", article.get("uniquekey", ""))
                        url = f"https://finance.eastmoney.com/a/{art_id}.html" if art_id else ""
                    digest = article.get("digest", article.get("content", ""))
                    if digest:
                        digest = re.sub(r"<[^>]+>", "", digest)[:300]
                    items.append(Item(
                        title=title,
                        url=url,
                        source="cn_economy",
                        raw_text=digest or "",
                        published_at=article.get("showtime", article.get("date", "")),
                        meta={"sub_source": "东方财富"},
                    ))
        except Exception:
            pass

    filtered = filter_by_time(items, since, until)
    return make_result("cn_economy", filtered)
