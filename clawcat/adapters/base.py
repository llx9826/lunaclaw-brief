"""Adapter base — shared utilities for all data source adapters."""

from __future__ import annotations

from datetime import datetime

import httpx

from clawcat.schema.item import FetchResult, Item

DEFAULT_TIMEOUT = 15


def new_client(timeout: int = DEFAULT_TIMEOUT, follow_redirects: bool = False, **kwargs) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects, **kwargs)


def filter_by_time(
    items: list[Item],
    since: datetime,
    until: datetime,
) -> list[Item]:
    """Soft-filter items outside the time window (1-day buffer for timezone safety).

    Precise filtering happens in the dedup node with exact time comparison.
    """
    from datetime import timedelta
    buffered_since = since - timedelta(days=1)
    result = []
    for item in items:
        dt = item.published_datetime
        if dt is None:
            result.append(item)  # keep items without dates; dedup will re-check
            continue
        if buffered_since <= dt <= until:
            result.append(item)
    return result


def make_result(
    source: str,
    items: list[Item],
    time_filtered: bool = True,
) -> FetchResult:
    return FetchResult(
        source=source,
        items=items,
        time_filtered=time_filtered,
    )
