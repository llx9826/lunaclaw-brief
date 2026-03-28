"""arXiv adapter — fetches papers via the arXiv API."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

from clawcat.adapters.base import filter_by_time, make_result, new_client
from clawcat.schema.item import FetchResult, Item

_NS = {"atom": "http://www.w3.org/2005/Atom"}

DEFAULT_CATEGORIES = ["cs.CV", "cs.LG", "cs.AI", "cs.CL"]


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    config = config or {}
    categories = config.get("categories", DEFAULT_CATEGORIES)
    max_results = config.get("max_results", 15)
    items: list[Item] = []

    async with new_client(follow_redirects=True) as client:
        for cat in categories:
            try:
                resp = await client.get(
                    "https://export.arxiv.org/api/query",
                    params={
                        "search_query": f"cat:{cat}",
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                        "max_results": str(max_results),
                    },
                )
                if resp.status_code != 200:
                    continue
                items.extend(_parse_atom(resp.text))
            except Exception:
                continue

    filtered = filter_by_time(items, since, until)
    return make_result("arxiv", filtered)


def _parse_atom(xml_text: str) -> list[Item]:
    items: list[Item] = []
    try:
        root = ET.fromstring(xml_text)
        for entry in root.findall("atom:entry", _NS):
            title_el = entry.find("atom:title", _NS)
            if title_el is None or not title_el.text:
                continue
            title = " ".join(title_el.text.strip().split())
            summary_el = entry.find("atom:summary", _NS)
            summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
            id_el = entry.find("atom:id", _NS)
            url = id_el.text.strip() if id_el is not None and id_el.text else ""
            pub_el = entry.find("atom:published", _NS)
            published = pub_el.text if pub_el is not None else ""
            arxiv_id = url.split("/abs/")[-1] if "/abs/" in url else ""
            categories = [c.get("term", "") for c in entry.findall("atom:category", _NS)]
            items.append(Item(
                title=title,
                url=url,
                source="arxiv",
                raw_text=summary[:500],
                published_at=published,
                meta={"arxiv_id": arxiv_id, "categories": categories},
            ))
    except ET.ParseError:
        pass
    return items
