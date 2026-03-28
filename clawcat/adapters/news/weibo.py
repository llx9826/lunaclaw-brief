"""Weibo Hot Search adapter — Chinese social media trending topics."""

from __future__ import annotations

from datetime import datetime

from clawcat.adapters.base import make_result, new_client
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
                "https://weibo.com/ajax/side/hotSearch",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for entry in data.get("data", {}).get("realtime", [])[:20]:
                    word = entry.get("word", "")
                    if not word:
                        continue
                    items.append(Item(
                        title=word,
                        url=f"https://s.weibo.com/weibo?q=%23{word}%23",
                        source="weibo",
                        raw_text=entry.get("label_name", ""),
                        published_at=datetime.now().isoformat(),
                        meta={
                            "hot_num": entry.get("num", 0),
                            "is_hot": entry.get("is_hot", 0),
                            "sub_source": "微博热搜",
                        },
                    ))
        except Exception:
            pass

    return make_result("weibo", items, time_filtered=False)
