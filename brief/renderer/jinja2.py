"""LunaClaw Brief — Jinja2 Renderer + PDF Generation

Renders ReportDraft into HTML (with embedded Luna logo) and optionally PDF.
The logo is base64-encoded and inlined so the HTML is fully self-contained.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from brief.models import ReportDraft, PresetConfig
from brief.renderer.markdown_parser import parse_sections

try:
    from weasyprint import HTML as WeasyHTML  # type: ignore
    _WEASY_OK = True
except ImportError:
    _WEASY_OK = False


class Jinja2Renderer:
    """Jinja2-based HTML renderer with embedded logo and optional PDF output."""

    def __init__(self, template_dir: Path, static_dir: Path, output_dir: Path):
        self.template_dir = template_dir
        self.static_dir = static_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.env = Environment(
            loader=FileSystemLoader([str(template_dir), str(static_dir)]),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _load_logo_b64(self) -> str:
        """Load pre-computed base64 logo, or return empty string."""
        b64_path = self.static_dir / "luna_logo_b64.txt"
        if b64_path.exists():
            return b64_path.read_text(encoding="utf-8").strip()
        return ""

    def render(
        self,
        draft: ReportDraft,
        preset: PresetConfig,
        time_range: str,
        stats: dict,
    ) -> dict:
        template = self.env.get_template("report.html")
        sections = parse_sections(draft.markdown)
        luna_logo_b64 = self._load_logo_b64()

        html = template.render(
            title=f"{preset.display_name} — {draft.issue_label}",
            display_name=preset.display_name,
            issue_label=draft.issue_label,
            time_range=time_range,
            stats=stats,
            sections=sections,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            luna_logo_b64=luna_logo_b64,
            show_disclaimer=getattr(preset, "show_disclaimer", False),
        )

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = preset.name
        html_path = self.output_dir / f"{prefix}_{ts}.html"
        md_path = self.output_dir / f"{prefix}_{ts}.md"
        pdf_path: Optional[Path] = None

        html_path.write_text(html, encoding="utf-8")
        md_path.write_text(draft.markdown, encoding="utf-8")

        if _WEASY_OK:
            try:
                pdf_path = self.output_dir / f"{prefix}_{ts}.pdf"
                WeasyHTML(filename=str(html_path), media_type="screen").write_pdf(
                    str(pdf_path), presentational_hints=True
                )
            except Exception as e:
                print(f"⚠️ PDF generation failed: {e}")
                pdf_path = None

        return {
            "html_path": str(html_path),
            "md_path": str(md_path),
            "pdf_path": str(pdf_path) if pdf_path else None,
        }
