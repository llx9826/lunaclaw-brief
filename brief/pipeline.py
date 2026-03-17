"""LunaClaw Brief — Report Pipeline

8-stage pipeline with middleware hooks, structured logging, and
pluggable three-level memory system:

  Fetch → Score → Select → Dedup(Memory) → Edit(LLM) → Quality → Render → Output

Memory integration (via MemoryManager):
  L1 ItemStore    — item_id dedup during Dedup phase
  L2 TopicStore   — topic diversity reorder during Dedup phase
  L3 ContentStore — claim recall/save around Edit phase

Supports both synchronous (run) and streaming (run_stream) execution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

from brief.models import PresetConfig, ReportDraft
from brief.sources import create_sources
from brief.scoring import Scorer, Selector
from brief.memory import MemoryManager
from brief.editors import create_editor
from brief.quality import QualityChecker
from brief.renderer.jinja2 import Jinja2Renderer
from brief.sender import EmailSender, WebhookSender
from brief.middleware import (
    PipelineContext, MiddlewareChain,
    TimingMiddleware, MetricsMiddleware, PipelineMiddleware,
)
from brief.log import BriefLogger


def _make_issue_label(cycle: str) -> str:
    """Generate a date-based issue label.

    Daily  → "2026-03-17"
    Weekly → "03.10~03.16"
    """
    now = datetime.now()
    if cycle == "weekly":
        end = now
        start = end - timedelta(days=6)
        return f"{start.strftime('%m.%d')}~{end.strftime('%m.%d')}"
    return now.strftime("%Y-%m-%d")


class ReportPipeline:
    """Orchestrates the full report generation flow.

    Usage:
        pipeline = ReportPipeline(preset, global_config)
        pipeline.use(MyCustomMiddleware())
        result = pipeline.run(user_hint="focus on OCR")

        # Or streaming:
        for event in pipeline.run_stream(user_hint="..."):
            print(event)
    """

    def __init__(self, preset: PresetConfig, global_config: dict):
        self.preset = preset
        self.config = global_config
        self.project_root = Path(global_config.get("project_root", "."))
        self._chain = MiddlewareChain()
        self._log = BriefLogger("pipeline")

        self._chain.add(TimingMiddleware())
        self._chain.add(MetricsMiddleware())

    def use(self, mw: PipelineMiddleware) -> "ReportPipeline":
        """Register a custom middleware. Returns self for chaining."""
        self._chain.add(mw)
        return self

    def run(
        self,
        user_hint: str = "",
        send_email: bool = False,
    ) -> dict:
        """Synchronous entry point. Runs the async pipeline internally."""
        return asyncio.run(self._run_async(user_hint, send_email))

    def run_stream(
        self,
        user_hint: str = "",
    ) -> Generator[dict, None, None]:
        """Streaming entry point. Yields progress events as dicts.

        Event types:
          {"type": "phase", "phase": "fetch", "status": "done", ...}
          {"type": "chunk", "content": "...markdown chunk..."}
          {"type": "result", ...final result dict...}
        """
        yield from self._run_stream_sync(user_hint)

    def _create_memory_manager(self) -> MemoryManager:
        """Create the standard three-level memory manager."""
        data_dir = self.project_root / "data"
        llm_cfg = self.config.get("llm", {})
        llm = None
        try:
            from brief.llm import LLMClient
            llm = LLMClient(llm_cfg)
        except Exception:
            pass
        return MemoryManager.create_default(data_dir, llm=llm)

    async def _run_async(self, user_hint: str, send_email: bool) -> dict:
        p = self.preset
        ctx = PipelineContext(preset_name=p.name)
        self._chain.fire_pipeline_start(ctx)

        now = datetime.now()
        since = now - timedelta(days=p.time_range_days)
        time_range = f"{since.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"
        log = self._log.bind(preset=p.name)

        issue_label = _make_issue_label(p.cycle)
        ctx.issue_label = issue_label

        print(f"\n{'='*50}")
        print(f"🦞 LunaClaw Brief — {p.display_name}")
        print(f"{'='*50}")

        # ── Phase 1: Fetch ──
        self._chain.fire_phase_start("fetch", ctx)
        log.info(f"Phase 1: Fetch — {len(p.sources)} sources")
        sources = create_sources(p.sources, self.config)
        all_items = []
        sources_used = []
        for source in sources:
            try:
                items = await source.fetch(since, now)
                if items:
                    all_items.extend(items)
                    sources_used.append(source.name)
                    log.info(f"  ✅ {source.name}", count=len(items))
            except Exception as e:
                log.warn(f"  ❌ {source.name}", error=str(e)[:60])
        ctx.phase_counts["fetch"] = len(all_items)
        self._chain.fire_phase_end("fetch", ctx)
        log.info("Fetch complete", total=len(all_items), sources=len(sources_used))

        if not all_items:
            log.error("No items fetched, aborting.")
            return {"success": False, "error": "no_items"}

        # ── Phase 2: Score ──
        self._chain.fire_phase_start("score", ctx)
        scorer = Scorer(p)
        scored = scorer.score(all_items)
        ctx.phase_counts["score"] = len(scored)
        self._chain.fire_phase_end("score", ctx)
        log.info("Phase 2: Score", valid=len(scored))

        # ── Phase 3: Select ──
        self._chain.fire_phase_start("select", ctx)
        selector = Selector(p)
        selected = selector.select(scored)
        ctx.phase_counts["select"] = len(selected)
        self._chain.fire_phase_end("select", ctx)
        log.info("Phase 3: Select", selected=len(selected))

        # ── Phase 4: Dedup (Memory-driven) ──
        self._chain.fire_phase_start("dedup", ctx)
        memory = self._create_memory_manager()
        deduped = memory.filter_items(selected, p.name, p.dedup_window_days)
        dup_count = len(selected) - len(deduped)
        is_rerun = False

        if not deduped:
            log.warn("All items seen before — regenerating with existing material")
            deduped = selected
            is_rerun = True

        ctx.phase_counts["dedup"] = len(deduped)
        self._chain.fire_phase_end("dedup", ctx)
        log.info("Phase 4: Dedup (Memory)", kept=len(deduped), removed=dup_count,
                 rerun=is_rerun)

        # ── Phase 5: Edit (LLM) ──
        self._chain.fire_phase_start("edit", ctx)
        editor = create_editor(p, self.config)

        log.info(f"Phase 5: Edit (LLM) — {issue_label}")
        hint = user_hint
        if is_rerun:
            hint = (hint + "\n" if hint else "") + "（注意：本期为重新生成，请尽量提供不同的视角和表述。）"

        memory_context = memory.recall_all(p.name)
        draft = editor.generate(deduped, issue_label, hint, memory_context=memory_context)
        if not draft:
            log.error("LLM generation failed.")
            return {"success": False, "error": "llm_failed"}
        ctx.phase_counts["edit"] = draft.word_count
        self._chain.fire_phase_end("edit", ctx)
        log.info("Edit complete", chars=draft.word_count)

        # ── Phase 6: Quality ──
        self._chain.fire_phase_start("quality", ctx)
        checker = QualityChecker(p)
        qr = checker.check(draft.markdown)
        log.info(f"Phase 6: Quality — {'PASS' if qr.passed else 'FAIL'}", score=f"{qr.score:.0%}")
        if qr.issues:
            for issue in qr.issues:
                log.warn(f"  ⚠️ {issue}")

        if not qr.passed:
            log.info("Retrying generation for quality...")
            draft2 = editor.generate(
                deduped, issue_label,
                user_hint + "\n请确保所有章节完整。",
                memory_context=memory_context,
            )
            if draft2:
                qr2 = checker.check(draft2.markdown)
                if qr2.score > qr.score:
                    draft, qr = draft2, qr2
                    log.info("Retry improved quality", score=f"{qr.score:.0%}")
        self._chain.fire_phase_end("quality", ctx)

        # ── Phase 7: Render ──
        self._chain.fire_phase_start("render", ctx)
        template_dir = self.project_root / "templates"
        static_dir = self.project_root / "static"
        output_dir = self.project_root / "output"
        renderer = Jinja2Renderer(template_dir, static_dir, output_dir)

        stats = {
            "total_items": len(all_items),
            "sources_used": len(sources_used),
            "selected_items": len(deduped),
            "word_count": draft.word_count,
        }
        render_result = renderer.render(draft, p, time_range, stats)
        self._chain.fire_phase_end("render", ctx)
        log.info("Phase 7: Render", html=render_result["html_path"])
        if render_result.get("pdf_path"):
            log.info("  PDF generated", path=render_result["pdf_path"])

        # ── Memory Save (post-render, before output) ──
        if not is_rerun:
            memory.save_all(p.name, issue_label, deduped, draft.markdown)
            log.info("Memory saved", stores=[s.name for s in memory.stores])

        # ── Phase 8: Output (Email / Webhook) ──
        if send_email:
            self._chain.fire_phase_start("email", ctx)
            email_cfg = self.config.get("email", {})
            if email_cfg:
                log.info("Phase 8: Email — sending...")
                sender = EmailSender(email_cfg)
                html_content = Path(render_result["html_path"]).read_text(encoding="utf-8")
                subject = f"🦞 {p.display_name} — {issue_label}"
                sender.send(
                    subject=subject,
                    html_content=html_content,
                    text_content=draft.markdown[:2000],
                    attachment_path=render_result.get("pdf_path"),
                )
            webhook_cfg = self.config.get("webhook", {})
            if webhook_cfg and webhook_cfg.get("url"):
                wh = WebhookSender(webhook_cfg)
                wh.send(
                    f"🦞 {p.display_name} — {issue_label}",
                    draft.markdown[:2000],
                    render_result.get("html_path", ""),
                )
            self._chain.fire_phase_end("email", ctx)

        self._chain.fire_pipeline_end(ctx)

        print(f"\n{'='*50}")
        print(f"✅ {issue_label} — {p.display_name} generated!")
        print(f"{'='*50}\n")

        return {
            "success": True,
            "issue_label": issue_label,
            "preset": p.name,
            "quality_score": qr.score,
            "word_count": draft.word_count,
            "metrics": ctx.extras.get("metrics", {}),
            **render_result,
        }

    def _run_stream_sync(self, user_hint: str) -> Generator[dict, None, None]:
        """Streaming pipeline: yields events during execution."""
        p = self.preset
        now = datetime.now()
        since = now - timedelta(days=p.time_range_days)
        time_range = f"{since.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"

        issue_label = _make_issue_label(p.cycle)

        # Phase 1-4: run synchronously, yield phase events
        yield {"type": "phase", "phase": "fetch", "status": "start"}
        sources = create_sources(p.sources, self.config)
        all_items = []
        sources_used = []
        for source in sources:
            try:
                items = asyncio.run(source.fetch(since, now))
                if items:
                    all_items.extend(items)
                    sources_used.append(source.name)
            except Exception:
                pass
        yield {"type": "phase", "phase": "fetch", "status": "done", "count": len(all_items)}

        if not all_items:
            yield {"type": "error", "error": "no_items"}
            return

        yield {"type": "phase", "phase": "score", "status": "start"}
        scorer = Scorer(p)
        scored = scorer.score(all_items)
        yield {"type": "phase", "phase": "score", "status": "done", "count": len(scored)}

        yield {"type": "phase", "phase": "select", "status": "start"}
        selector = Selector(p)
        selected = selector.select(scored)
        yield {"type": "phase", "phase": "select", "status": "done", "count": len(selected)}

        yield {"type": "phase", "phase": "dedup", "status": "start"}
        memory = self._create_memory_manager()
        deduped = memory.filter_items(selected, p.name, p.dedup_window_days)
        is_rerun = not deduped
        if is_rerun:
            deduped = selected
        yield {"type": "phase", "phase": "dedup", "status": "done", "count": len(deduped), "rerun": is_rerun}

        # Phase 5: Streaming LLM generation
        yield {"type": "phase", "phase": "edit", "status": "start"}
        editor = create_editor(p, self.config)

        hint = user_hint
        if is_rerun:
            hint = (hint + "\n" if hint else "") + "（注意：本期为重新生成，请尽量提供不同的视角和表述。）"

        memory_context = memory.recall_all(p.name)

        markdown_chunks: list[str] = []
        for chunk in editor.generate_stream(deduped, issue_label, hint, memory_context=memory_context):
            markdown_chunks.append(chunk)
            yield {"type": "chunk", "content": chunk}

        full_markdown = "".join(markdown_chunks)
        full_markdown = editor._clean_markdown(full_markdown)
        yield {"type": "phase", "phase": "edit", "status": "done", "chars": len(full_markdown)}

        # Phase 6-7: Quality + Render
        draft = ReportDraft(markdown=full_markdown, issue_label=issue_label)

        checker = QualityChecker(p)
        qr = checker.check(draft.markdown)

        template_dir = self.project_root / "templates"
        static_dir = self.project_root / "static"
        output_dir = self.project_root / "output"
        renderer = Jinja2Renderer(template_dir, static_dir, output_dir)

        stats = {
            "total_items": len(all_items),
            "sources_used": len(sources_used),
            "selected_items": len(deduped),
            "word_count": draft.word_count,
        }
        render_result = renderer.render(draft, p, time_range, stats)

        if not is_rerun:
            memory.save_all(p.name, issue_label, deduped, draft.markdown)

        yield {
            "type": "result",
            "success": True,
            "issue_label": issue_label,
            "preset": p.name,
            "quality_score": qr.score,
            "word_count": draft.word_count,
            **render_result,
        }
