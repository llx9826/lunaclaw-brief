"""Render node — Jinja2 HTML + Playwright PDF generation.

Consumes Brief.model_dump() directly — no Markdown parsing.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from clawcat.config import get_settings
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)


def _ensure_dirs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def render_node(state: PipelineState) -> dict:
    """Render Brief → HTML (+ optional PDF via Playwright)."""
    brief = state.get("brief")
    if not brief:
        return {"error": "No brief to render"}

    settings = get_settings()
    output_dir = Path(settings.output_dir)
    template_dir = Path(settings.template_dir)
    static_dir = Path(settings.static_dir)
    _ensure_dirs(output_dir)

    env = Environment(
        loader=FileSystemLoader([str(template_dir), str(static_dir)]),
        autoescape=select_autoescape(["html", "xml"]),
    )

    try:
        template = env.get_template("report.html")
    except Exception:
        logger.error("Template not found, skipping render")
        return {"error": "Template not found"}

    brief_data = brief.model_dump()

    logo_b64 = ""
    logo_path = static_dir / "luna_logo_b64.txt"
    if logo_path.exists():
        logo_b64 = logo_path.read_text(encoding="utf-8").strip()

    html = template.render(
        brief=brief_data,
        title=brief.title,
        issue_label=brief.issue_label,
        time_range=brief_data["time_range"],
        sections=brief_data["sections"],
        executive_summary=brief.executive_summary,
        metadata=brief_data["metadata"],
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        luna_logo_b64=logo_b64,
        brand_full_name=settings.brand.full_name,
        brand_tagline=settings.brand.tagline,
        brand_author=settings.brand.author,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = brief.issue_label.replace(" ", "_").replace("/", "-")
    prefix = f"{brief.report_type}_{safe_label}"
    html_path = output_dir / f"{prefix}_{ts}.html"
    json_path = output_dir / f"{prefix}_{ts}.json"

    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(
        json.dumps(brief_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Rendered HTML: %s", html_path)

    pdf_path_str = None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf_out = output_dir / f"{prefix}_{ts}.pdf"
            page.pdf(path=str(pdf_out), format="A4", print_background=True)
            browser.close()
            pdf_path_str = str(pdf_out)
            logger.info("Exported PDF: %s", pdf_out)
    except Exception as e:
        logger.warning("PDF export skipped: %s", e)

    return {
        "html_path": str(html_path),
        "pdf_path": pdf_path_str or "",
        "json_path": str(json_path),
    }
