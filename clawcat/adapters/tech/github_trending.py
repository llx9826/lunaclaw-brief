"""GitHub adapter — multi-strategy repo search.

Strategies:
  updated  — recently pushed, sorted by update time → active development
  created  — created within time window, sorted by stars → brand-new projects
  rising   — created in last 90 days + pushed recently + sorted by stars
             → "rising stars" that are new AND gaining traction fast

Config (set by Planner via SourceSelection.config):
  queries      list[str]   Search keywords. REQUIRED.
  strategies   list[str]   Default: ["rising", "created", "updated"]
  min_stars    int         Minimum stars. Default: 3
  per_query    int         Results per query per strategy. Default: 8
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from clawcat.adapters.base import filter_by_time, make_result, new_client
from clawcat.schema.item import FetchResult, Item

logger = logging.getLogger(__name__)

DEFAULT_STRATEGIES = ["rising", "created", "updated"]
CONCURRENT_LIMIT = 3  # max parallel GitHub API calls to avoid rate-limit


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    config = config or {}
    queries: list[str] = config.get("queries", [])
    strategies: list[str] = config.get("strategies", DEFAULT_STRATEGIES)
    min_stars: int = config.get("min_stars", 3)
    per_query: int = config.get("per_query", 8)
    token: str = config.get("github_token", "")

    if not queries:
        logger.warning("github_trending: no queries provided, skipping")
        return make_result("github_trending", [])

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    seen: set[str] = set()
    items: list[Item] = []
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

    async def _search_one(q_str: str, sort: str, strategy: str):
        async with semaphore:
            await asyncio.sleep(0.5)  # gentle pacing
            try:
                async with new_client() as client:
                    resp = await client.get(
                        "https://api.github.com/search/repositories",
                        params={"q": q_str, "sort": sort, "order": "desc", "per_page": str(per_query)},
                        headers=headers,
                    )
                    if resp.status_code != 200:
                        return
                    for repo in resp.json().get("items", []):
                        name = repo["full_name"]
                        if name in seen:
                            continue
                        seen.add(name)
                        if repo.get("stargazers_count", 0) < min_stars:
                            continue
                        items.append(_repo_to_item(repo, strategy))
            except Exception as e:
                logger.warning("github search failed (sort=%s): %s", sort, e)

    since_date = since.strftime("%Y-%m-%d")
    rising_since = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    tasks = []
    for query in queries:
        for strategy in strategies:
            sort, q_str = _build_params(strategy, query, since_date, rising_since)
            tasks.append(_search_one(q_str, sort, strategy))

    await asyncio.gather(*tasks)

    filtered = filter_by_time(items, since, until)
    logger.info("github_trending: %d repos (%d queries × %d strategies)",
                len(filtered), len(queries), len(strategies))
    return make_result("github_trending", filtered)


def _build_params(strategy: str, query: str, since_date: str, rising_since: str) -> tuple[str, str]:
    """Return (sort_field, query_string) for a given strategy."""
    if strategy == "rising":
        return "stars", f"{query} created:>{rising_since} pushed:>{since_date}"
    elif strategy == "created":
        return "stars", f"{query} created:>{since_date}"
    elif strategy == "updated":
        return "updated", f"{query} pushed:>{since_date}"
    else:
        return "stars", f"{query} pushed:>{since_date}"


def _repo_to_item(repo: dict, strategy: str) -> Item:
    """Convert a GitHub API repo object to an Item with rich metadata."""
    name = repo["full_name"]
    desc = (repo.get("description") or "")[:500]
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    created = repo.get("created_at", "")
    updated = repo.get("updated_at", "")

    is_new = strategy in ("created", "rising")
    published = created if strategy == "created" else updated

    topics = repo.get("topics", [])
    lang = repo.get("language") or ""
    license_info = repo.get("license") or {}
    license_name = license_info.get("spdx_id", "") if isinstance(license_info, dict) else ""

    badges = [f"⭐ {stars}"]
    if lang:
        badges.append(lang)
    if license_name and license_name != "NOASSERTION":
        badges.append(license_name)
    if strategy == "rising":
        badges.append("📈 rising")
    elif strategy == "created":
        badges.append("🆕 new")

    raw_text = f"{desc}\n{' · '.join(badges)}"
    if topics:
        raw_text += f"\ntopics: {', '.join(topics[:8])}"

    return Item(
        title=name,
        url=repo["html_url"],
        source="github_trending",
        raw_text=raw_text,
        published_at=published,
        meta={
            "stars": stars,
            "forks": forks,
            "open_issues": repo.get("open_issues_count", 0),
            "language": lang,
            "license": license_name,
            "topics": topics,
            "created_at": created,
            "updated_at": updated,
            "strategy": strategy,
        },
    )
