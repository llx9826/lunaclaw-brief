"""Fetch node — dynamically loads adapters and fetches items within time range.

Implements Layer 1 of freshness guarantee: passes since/until to each adapter.
Uses asyncio.to_thread to run the async fetch logic from a sync LangGraph node.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from datetime import datetime

from clawcat.schema.item import FetchResult, Item
from clawcat.state import PipelineState
from clawcat.utils.time import parse_naive

logger = logging.getLogger(__name__)


def _resolve_module(module_path: str):
    mod = importlib.import_module(module_path)
    if not hasattr(mod, "fetch"):
        raise AttributeError(f"{module_path} has no fetch() function")
    return mod.fetch


async def _fetch_one(
    source_name: str,
    module_path: str,
    since: datetime,
    until: datetime,
    config: dict,
) -> FetchResult:
    try:
        fetch_fn = _resolve_module(module_path)
        result = await fetch_fn(since=since, until=until, config=config)
        logger.info("Fetched %d items from %s", len(result.items), source_name)
        return result
    except Exception as e:
        logger.warning("Failed to fetch from %s: %s", source_name, e)
        return FetchResult(source=source_name, items=[])


async def _fetch_all(task, registry: dict) -> list[FetchResult]:
    since = parse_naive(task.since) if task.since else datetime.now()
    until = parse_naive(task.until) if task.until else datetime.now()

    coros = []
    for sel in task.selected_sources:
        entry = registry.get(sel.source_name, {})
        module_path = entry.get("module", f"clawcat.adapters.tech.{sel.source_name}")
        config = {**entry.get("default_config", {}), **sel.config}
        coros.append(_fetch_one(sel.source_name, module_path, since, until, config))

    return await asyncio.gather(*coros)


def fetch_node(state: PipelineState) -> dict:
    """Fetch: TaskConfig → list[Item] from all selected sources."""
    import json
    from pathlib import Path

    task = state.get("task_config")
    if not task:
        return {"error": "No task_config available", "raw_items": []}

    registry_path = Path("clawcat/adapters/registry.json")
    registry: dict[str, dict] = {}
    if registry_path.exists():
        for entry in json.loads(registry_path.read_text(encoding="utf-8")):
            registry[entry["name"]] = entry

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = pool.submit(asyncio.run, _fetch_all(task, registry)).result()
    else:
        results = asyncio.run(_fetch_all(task, registry))

    all_items: list[Item] = []
    for r in results:
        all_items.extend(r.items)

    logger.info("Total fetched: %d items from %d sources", len(all_items), len(results))
    return {"raw_items": all_items}
