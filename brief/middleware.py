"""LunaClaw Brief — Pipeline Middleware

可插拔的管线钩子，在各阶段前后执行自定义逻辑。

用法:
    pipeline = ReportPipeline(preset, config)
    pipeline.use(TimingMiddleware())
    pipeline.use(MetricsMiddleware())
    result = pipeline.run()

所有中间件实现 PipelineMiddleware 接口，pipeline 内部通过
MiddlewareChain 按顺序调用。
"""

from __future__ import annotations

import time
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PipelineContext:
    """管线上下文，贯穿全阶段，中间件可读写"""

    preset_name: str = ""
    issue_label: str = ""
    started_at: float = field(default_factory=time.time)

    # 各阶段计时（秒）
    phase_timings: dict[str, float] = field(default_factory=dict)

    # 各阶段条目统计
    phase_counts: dict[str, int] = field(default_factory=dict)

    # 任意扩展数据
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at


class PipelineMiddleware(ABC):
    """中间件基类，按需重写"""

    def on_phase_start(self, phase: str, ctx: PipelineContext):
        pass

    def on_phase_end(self, phase: str, ctx: PipelineContext):
        pass

    def on_pipeline_start(self, ctx: PipelineContext):
        pass

    def on_pipeline_end(self, ctx: PipelineContext):
        pass


class MiddlewareChain:
    """中间件链"""

    def __init__(self):
        self._middlewares: list[PipelineMiddleware] = []

    def add(self, mw: PipelineMiddleware):
        self._middlewares.append(mw)

    def fire_pipeline_start(self, ctx: PipelineContext):
        for mw in self._middlewares:
            mw.on_pipeline_start(ctx)

    def fire_pipeline_end(self, ctx: PipelineContext):
        for mw in self._middlewares:
            mw.on_pipeline_end(ctx)

    def fire_phase_start(self, phase: str, ctx: PipelineContext):
        for mw in self._middlewares:
            mw.on_phase_start(phase, ctx)

    def fire_phase_end(self, phase: str, ctx: PipelineContext):
        for mw in self._middlewares:
            mw.on_phase_end(phase, ctx)


# ── 内置中间件 ──


class TimingMiddleware(PipelineMiddleware):
    """记录每个阶段耗时"""

    def __init__(self):
        self._phase_start: dict[str, float] = {}

    def on_phase_start(self, phase: str, ctx: PipelineContext):
        self._phase_start[phase] = time.time()

    def on_phase_end(self, phase: str, ctx: PipelineContext):
        start = self._phase_start.get(phase)
        if start:
            ctx.phase_timings[phase] = round(time.time() - start, 2)

    def on_pipeline_end(self, ctx: PipelineContext):
        total = ctx.elapsed
        print(f"\n⏱  Pipeline 总耗时: {total:.1f}s")
        for phase, dur in ctx.phase_timings.items():
            bar = "█" * int(dur / total * 20) if total > 0 else ""
            print(f"   {phase:12s} {dur:6.1f}s  {bar}")


class MetricsMiddleware(PipelineMiddleware):
    """收集管线指标，存入 context"""

    def on_pipeline_end(self, ctx: PipelineContext):
        ctx.extras["metrics"] = {
            "total_seconds": round(ctx.elapsed, 1),
            "phase_timings": ctx.phase_timings,
            "phase_counts": ctx.phase_counts,
            "preset": ctx.preset_name,
            "issue_label": ctx.issue_label,
            "completed_at": datetime.now().isoformat(),
        }
