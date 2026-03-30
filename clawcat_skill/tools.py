"""clawcat_skill.tools — Three tool functions for host-AI skill mode.

All functions are pure I/O: no LLM calls.  The host AI handles planning,
writing, and quality checking; this module handles data fetching, dedup,
and rendering.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("clawcat_skill")

_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY_PATH = _ROOT / "clawcat" / "adapters" / "registry.json"


# ---------------------------------------------------------------------------
# 1. plan_report — intent parsing + registry lookup (no LLM)
# ---------------------------------------------------------------------------

_PERIOD_PATTERNS: list[tuple[str, str]] = [
    (r"周报|weekly|每周|本周|上周|近一周", "weekly"),
    (r"日报|daily|每日|今[天日]|昨[天日]|近24", "daily"),
]

_TOPIC_PATTERNS: list[tuple[str, list[str]]] = [
    (r"[Aa]\s*股|沪深|上证|深证|创业板", ["finance", "stock"]),
    (r"港股|恒生|HK\s*stock", ["finance", "stock"]),
    (r"美股|纳斯达克|标普|道琼斯|US\s*stock", ["finance", "stock"]),
    (r"宏观|经济|PMI|CPI|GDP", ["finance", "macro", "economy"]),
    (r"OCR|文字识别|文档智能", ["tech", "ai", "cv"]),
    (r"大模型|LLM|GPT|语言模型", ["tech", "ai"]),
    (r"AI|人工智能|机器学习|深度学习", ["tech", "ai"]),
    (r"CV|计算机视觉|computer\s*vision", ["tech", "ai", "cv"]),
    (r"NLP|自然语言", ["tech", "ai", "nlp"]),
    (r"具身智能|embodied|robot", ["tech", "ai"]),
    (r"开源|open\s*source|github", ["tech", "open-source"]),
]


def _infer_period(query: str) -> str:
    for pattern, period in _PERIOD_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return period
    return "daily"


def _infer_domains(query: str) -> list[str]:
    domains: list[str] = []
    for pattern, tags in _TOPIC_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            for t in tags:
                if t not in domains:
                    domains.append(t)
    return domains or ["tech", "ai"]


def _load_registry() -> list[dict]:
    if _REGISTRY_PATH.exists():
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return []


def _match_sources(registry: list[dict], domains: list[str]) -> list[dict]:
    """Select sources whose domains overlap with the inferred domains."""
    matched = []
    for entry in registry:
        src_domains = entry.get("domains", [])
        if set(src_domains) & set(domains):
            matched.append({
                "name": entry["name"],
                "module": entry.get("module", ""),
                "domains": src_domains,
                "description": entry.get("description", ""),
                "best_for": entry.get("best_for", ""),
                "config_params": entry.get("config_params", {}),
                "config_guidance": entry.get("config_guidance", ""),
            })
    return matched


def plan_report(query: str) -> dict:
    """Parse user intent and return suggested report configuration.

    This is rule-based (no LLM).  The host AI should review the suggestion
    and adjust topic, sources, and structure as it sees fit.

    Args:
        query: Natural-language report request, e.g. "OCR 技术周报".

    Returns:
        {
            "suggested_config": {
                "topic": str,
                "period": "daily" | "weekly",
                "inferred_domains": [...],
                "since": ISO str,
                "until": ISO str,
            },
            "matched_sources": [ { name, module, domains, description, ... } ],
            "all_sources": [ ... ],          # full registry for reference
            "user_profile": { ... } | null,
        }
    """
    period = _infer_period(query)
    domains = _infer_domains(query)

    now = datetime.now()
    if period == "weekly":
        since = (now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
    else:
        since = (now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    until = now.isoformat()

    registry = _load_registry()
    matched = _match_sources(registry, domains)

    profile: dict | None = None
    try:
        from clawcat.schema.user import UserProfile
        from clawcat.config import get_settings
        settings = get_settings()
        up = UserProfile.load(Path(settings.user_profile_path))
        profile = up.model_dump()
    except Exception:
        pass

    return {
        "suggested_config": {
            "topic": query.strip(),
            "period": period,
            "inferred_domains": domains,
            "since": since,
            "until": until,
        },
        "matched_sources": matched,
        "all_sources": registry,
        "user_profile": profile,
    }


# ---------------------------------------------------------------------------
# 2. fetch_data — parallel fetch + dedup (no LLM)
# ---------------------------------------------------------------------------

def fetch_data(task_config: dict) -> dict:
    """Fetch, filter, and deduplicate items from selected sources.

    Args:
        task_config: A dict matching the TaskConfig schema::

            {
                "topic": "OCR技术",
                "period": "weekly",
                "selected_sources": [
                    {"source_name": "hackernews", "config": {"queries": ["OCR"]}},
                    {"source_name": "36kr",       "config": {"queries": ["OCR"]}}
                ],
                "since": "2026-03-09T00:00:00",
                "until": "2026-03-16T12:00:00",
                "max_items": 30
            }

    Returns:
        {
            "items": [ { title, url, source, raw_text, published_at, item_id, ... } ],
            "stats": {
                "total_fetched": int,
                "after_dedup": int,
                "sources_used": [str]
            }
        }
    """
    from clawcat.schema.task import TaskConfig, SourceSelection
    from clawcat.schema.item import Item
    from clawcat.utils.time import parse_naive

    sources_raw = task_config.get("selected_sources", [])
    source_selections = []
    for s in sources_raw:
        if isinstance(s, dict):
            source_selections.append(SourceSelection(**s))
        else:
            source_selections.append(s)

    tc = TaskConfig(
        topic=task_config.get("topic", ""),
        period=task_config.get("period", "daily"),
        selected_sources=source_selections,
        since=task_config.get("since", ""),
        until=task_config.get("until", ""),
        max_items=task_config.get("max_items", 30),
        focus_areas=task_config.get("focus_areas", []),
    )

    # --- Fetch (reuse clawcat async fetch) ---
    registry: dict[str, dict] = {}
    if _REGISTRY_PATH.exists():
        for entry in json.loads(_REGISTRY_PATH.read_text(encoding="utf-8")):
            registry[entry["name"]] = entry

    from clawcat.nodes.fetch import _fetch_all

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = pool.submit(asyncio.run, _fetch_all(tc, registry)).result()
    else:
        results = asyncio.run(_fetch_all(tc, registry))

    all_items: list[Item] = []
    sources_used: list[str] = []
    for r in results:
        all_items.extend(r.items)
        if r.items:
            sources_used.append(r.source)

    total_fetched = len(all_items)

    # --- Dedup (inline, avoid PipelineState dependency) ---
    since_dt = parse_naive(tc.since) if tc.since else None
    until_dt = parse_naive(tc.until) if tc.until else None

    from clawcat.nodes.dedup import _load_seen_ids
    seen_ids = _load_seen_ids()
    filtered: list[Item] = []

    for item in all_items:
        if item.item_id in seen_ids:
            continue
        pub_dt = item.published_datetime
        if pub_dt is not None and since_dt and pub_dt < since_dt:
            continue
        if pub_dt is not None and until_dt and pub_dt > until_dt:
            continue
        seen_ids.add(item.item_id)
        filtered.append(item)

    logger.info("fetch_data: %d fetched → %d after dedup", total_fetched, len(filtered))

    return {
        "items": [item.model_dump() for item in filtered],
        "stats": {
            "total_fetched": total_fetched,
            "after_dedup": len(filtered),
            "sources_used": sources_used,
        },
    }


# ---------------------------------------------------------------------------
# 3. render_report — Jinja2 HTML + Playwright PDF/PNG (no LLM)
# ---------------------------------------------------------------------------

def render_report(brief: dict, output_dir: str = "output") -> dict:
    """Render a Brief dict into HTML, PDF, PNG, Markdown, and JSON.

    Args:
        brief: A dict conforming to the Brief schema::

            {
                "schema_version": "1.0",
                "report_type": "weekly",
                "title": "OCR 技术 · 每周概览",
                "issue_label": "2026-03-16",
                "time_range": {
                    "user_requested": "...",
                    "resolved_start": "...",
                    "resolved_end": "...",
                    "report_generated": "...",
                },
                "executive_summary": "...",
                "sections": [ ... ],
                "metadata": { ... }
            }

        output_dir: Directory to write output files.

    Returns:
        {
            "html_path": str,
            "pdf_path": str,
            "png_path": str,
            "json_path": str,
            "md_path": str
        }
    """
    from clawcat.schema.brief import Brief
    from clawcat.config import get_settings

    brief_obj = Brief.model_validate(brief)
    settings = get_settings()

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    template_dir = Path(settings.template_dir)
    static_dir = Path(settings.static_dir)

    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader([str(template_dir), str(static_dir)]),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template("report.html")
    brief_data = brief_obj.model_dump()

    logo_b64 = ""
    logo_path = static_dir / "luna_logo_b64.txt"
    if logo_path.exists():
        logo_b64 = logo_path.read_text(encoding="utf-8").strip()

    html = template.render(
        brief=brief_data,
        title=brief_obj.title,
        issue_label=brief_obj.issue_label,
        time_range=brief_data["time_range"],
        sections=brief_data["sections"],
        executive_summary=brief_obj.executive_summary,
        metadata=brief_data["metadata"],
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        luna_logo_b64=logo_b64,
        brand_full_name=settings.brand.full_name,
        brand_tagline=settings.brand.tagline,
        brand_author=settings.brand.author,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = brief_obj.issue_label.replace(" ", "_").replace("/", "-")
    prefix = f"{brief_obj.report_type}_{safe_label}"

    html_path = out / f"{prefix}_{ts}.html"
    json_path = out / f"{prefix}_{ts}.json"
    md_path = out / f"{prefix}_{ts}.md"

    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(
        json.dumps(brief_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Rendered HTML: %s", html_path)

    try:
        md_template = env.get_template("report.md.j2")
        md_text = md_template.render(
            title=brief_obj.title,
            time_range=brief_data["time_range"],
            sections=brief_data["sections"],
            executive_summary=brief_obj.executive_summary,
            metadata=brief_data["metadata"],
            brand_full_name=settings.brand.full_name,
            brand_tagline=settings.brand.tagline,
            brand_author=settings.brand.author,
        )
        md_path.write_text(md_text, encoding="utf-8")
    except Exception as e:
        logger.warning("Markdown render skipped: %s", e)

    pdf_path_str = ""
    png_path_str = ""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")

            pdf_page = browser.new_page()
            pdf_page.set_content(html, wait_until="networkidle")
            pdf_out = out / f"{prefix}_{ts}.pdf"
            pdf_page.pdf(path=str(pdf_out), format="A4", print_background=True)
            pdf_path_str = str(pdf_out)
            pdf_page.close()

            png_ctx = browser.new_context(
                viewport={"width": 390, "height": 800},
                device_scale_factor=2,
            )
            png_page = png_ctx.new_page()
            png_page.set_content(html, wait_until="networkidle")
            png_out = out / f"{prefix}_{ts}.png"
            png_page.screenshot(path=str(png_out), full_page=True)
            png_path_str = str(png_out)
            png_page.close()

            browser.close()
            logger.info("Exported PDF: %s / PNG: %s", pdf_out, png_out)
    except Exception as e:
        logger.warning("PDF/PNG export skipped: %s", e)

    return {
        "html_path": str(html_path),
        "pdf_path": pdf_path_str,
        "png_path": png_path_str,
        "json_path": str(json_path),
        "md_path": str(md_path) if md_path.exists() else "",
    }
