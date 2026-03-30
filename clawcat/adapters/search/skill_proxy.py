"""Skill Proxy adapter — bridges external ClawHub/Cursor search skills into ClawCat.

This adapter dynamically imports and calls external skill modules that follow
the common search-skill pattern (a callable returning a list of results with
title/url/snippet/date fields).

Config (via SourceSelection.config):
  skill_module   str        Python module path to import, e.g. "miaoda_unified.search"
  skill_function str        Function name to call. Default: "search".
  queries        list[str]  Search keywords to pass.
  max_results    int        Max results per query. Default: 10.
  extra_config   dict       Extra kwargs forwarded to the skill function.

The skill function is expected to have one of these signatures:
  - search(query: str, **kwargs) -> list[dict]
  - search(queries: list[str], **kwargs) -> list[dict]

Each result dict should contain at least: title, url.
Optional fields: snippet/summary/body, date/published_at, source.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from datetime import datetime

from clawcat.adapters.base import filter_by_time, make_result
from clawcat.schema.item import FetchResult, Item

logger = logging.getLogger(__name__)


def _normalize_result(raw: dict, source_label: str) -> Item:
    """Convert a skill result dict into a unified Item."""
    title = raw.get("title", "")
    url = raw.get("url") or raw.get("link", "")
    body = raw.get("snippet") or raw.get("summary") or raw.get("body") or raw.get("content", "")
    pub = raw.get("date") or raw.get("published_at") or raw.get("pub_date", "")
    sub_source = raw.get("source") or raw.get("provider", source_label)

    return Item(
        title=title,
        url=url,
        source=source_label,
        raw_text=str(body)[:500],
        published_at=pub if pub else None,
        meta={"sub_source": sub_source, "adapter": "skill_proxy"},
    )


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    config = config or {}
    skill_module: str = config.get("skill_module", "")
    skill_function: str = config.get("skill_function", "search")
    queries: list[str] = config.get("queries", [])
    max_results: int = config.get("max_results", 10)
    extra_config: dict = config.get("extra_config", {})
    source_label: str = config.get("source_label", skill_module.split(".")[-1] if skill_module else "skill_proxy")

    if not skill_module:
        logger.warning("skill_proxy: no skill_module configured, skipping")
        return make_result("skill_proxy", [])

    if not queries:
        logger.warning("skill_proxy: no queries provided, skipping")
        return make_result("skill_proxy", [])

    try:
        mod = importlib.import_module(skill_module)
        fn = getattr(mod, skill_function)
    except (ImportError, AttributeError) as e:
        logger.error("skill_proxy: failed to import %s.%s: %s", skill_module, skill_function, e)
        return make_result(source_label, [])

    items: list[Item] = []
    seen_urls: set[str] = set()

    def _call_sync():
        results = []
        for query in queries:
            try:
                raw = fn(query=query, max_results=max_results, **extra_config)
                if isinstance(raw, list):
                    results.extend(raw)
                elif isinstance(raw, dict) and "results" in raw:
                    results.extend(raw["results"])
            except Exception as e:
                logger.warning("skill_proxy: query '%s' via %s failed: %s", query, skill_module, e)
        return results

    raw_results = await asyncio.to_thread(_call_sync)

    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        item = _normalize_result(raw, source_label)
        if item.url and item.url in seen_urls:
            continue
        if item.url:
            seen_urls.add(item.url)
        items.append(item)

    filtered = filter_by_time(items, since, until)
    logger.info("skill_proxy[%s]: %d raw → %d deduped → %d filtered",
                source_label, len(raw_results), len(items), len(filtered))
    return make_result(source_label, filtered)
