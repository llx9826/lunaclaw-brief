"""Hugging Face Daily Papers adapter."""

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
                "https://huggingface.co/api/daily_papers",
                params={"limit": "30"},
            )
            if resp.status_code == 200:
                for paper in resp.json():
                    title = paper.get("title", "")
                    if not title:
                        continue
                    paper_id = paper.get("paper", {}).get("id", "")
                    items.append(Item(
                        title=title,
                        url=f"https://huggingface.co/papers/{paper_id}" if paper_id else "",
                        source="hf_papers",
                        raw_text=paper.get("paper", {}).get("summary", "")[:500],
                        published_at=paper.get("publishedAt", ""),
                        meta={
                            "upvotes": paper.get("paper", {}).get("upvotes", 0),
                        },
                    ))
        except Exception:
            pass

    filtered = filter_by_time(items, since, until)
    return make_result("hf_papers", filtered)
