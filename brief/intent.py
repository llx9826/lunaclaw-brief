"""LunaClaw Brief — Intent Parser (Agent Layer)

Parses user natural language input into a structured ReportRequest,
separating topic identification from period detection, then resolving
to the best matching preset.

Architecture:
  User hint → parse_topic() + parse_period()
            → resolve_preset(topic, period)
            → ReportRequest

Three resolution tiers:
  1. Regex (instant, free, deterministic)
  2. Preset lookup by (topic, period) combination
  3. LLM fallback (slow, costly, for ambiguous inputs)

When no preset matches, the parser signals auto_created=True so the
caller can trigger dynamic preset generation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from brief.models import ReportRequest


# ── Topic keyword table ──────────────────────────────────────────
# Each topic maps to regex patterns that identify it in user input.
# Order matters: more specific topics checked first.

TOPIC_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("stock_a",  re.compile(r"a\s*股|a[-\s]?share|沪深|上证|深证|创业板|科创板|北交所", re.I)),
    ("stock_hk", re.compile(r"港股|hk(?:\s*stock)?(?=\s|$)|hang\s*seng|恒[生指]|hong\s*kong|南向资金", re.I)),
    ("stock_us", re.compile(r"美股|us\s*stock|nasdaq|s&?p\s*500|道琼斯|wall\s*street|纳斯达克", re.I)),
    ("finance",  re.compile(r"金融|finance|投资|投行|基金|理财|证券|券商", re.I)),
    ("ai",       re.compile(r"ai|人工智能|机器学习|深度学习|llm|cv|ocr|多模态|大模型|agent|transformer", re.I)),
    ("education", re.compile(r"教育|education|教学|课程|学术|高校|考研|留学", re.I)),
    ("crypto",   re.compile(r"加密|crypto|比特币|bitcoin|以太坊|ethereum|web3|defi", re.I)),
    ("healthcare", re.compile(r"医疗|医药|health|医学|临床|生物科技|biotech|制药", re.I)),
    ("energy",   re.compile(r"能源|新能源|光伏|锂电|风电|solar|电池|储能|碳中和", re.I)),
]

# ── Period keyword table ──────────────────────────────────────────

PERIOD_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("weekly",  re.compile(r"周报|weekly|每周|本周|这周|一周", re.I)),
    ("daily",   re.compile(r"日报|daily|每日|今日|今天|每天", re.I)),
]


class IntentParser:
    """Parses user input into a structured ReportRequest.

    Usage:
        parser = IntentParser(presets_dict)
        request = parser.parse("帮我生成A股周报")
        # → ReportRequest(topic="stock_a", period="weekly", preset_name="stock_a_weekly")
    """

    def __init__(self, presets: dict, llm_config: dict | None = None):
        self._presets = presets
        self._llm_config = llm_config or {}
        self._topic_index = self._build_topic_index()

    def _build_topic_index(self) -> dict[tuple[str, str], str]:
        """Build (topic, period) → preset_name lookup from registered presets."""
        index: dict[tuple[str, str], str] = {}
        for name, preset in self._presets.items():
            topic = getattr(preset, "topic", "") or ""
            cycle = getattr(preset, "cycle", "") or ""
            if topic and cycle:
                index[(topic, cycle)] = name
        return index

    def parse(
        self,
        hint: str,
        explicit_preset: str = "",
    ) -> ReportRequest:
        """Parse user hint into ReportRequest.

        Resolution priority:
          1. Explicit preset (--preset flag) → skip parsing
          2. Regex topic + period extraction → preset lookup
          3. LLM intent classification (if regex finds nothing)
          4. Default fallback
        """
        if explicit_preset and explicit_preset in self._presets:
            preset = self._presets[explicit_preset]
            return ReportRequest(
                topic=getattr(preset, "topic", "") or "",
                period=getattr(preset, "cycle", "daily"),
                raw_hint=hint,
                preset_name=explicit_preset,
                confidence=1.0,
            )

        if not hint:
            return self._default_request("")

        topic = self._parse_topic(hint)
        period = self._parse_period(hint)
        focus = self._extract_focus(hint, topic)

        if topic:
            preset_name = self._resolve_preset(topic, period)
            if preset_name:
                return ReportRequest(
                    topic=topic,
                    period=period,
                    focus=focus,
                    raw_hint=hint,
                    preset_name=preset_name,
                    confidence=0.9,
                )
            # Topic recognized but no matching preset exists
            return ReportRequest(
                topic=topic,
                period=period,
                focus=focus,
                raw_hint=hint,
                preset_name="",
                confidence=0.7,
                auto_created=True,
            )

        # Regex couldn't identify topic — try LLM
        llm_result = self._classify_with_llm(hint)
        if llm_result:
            return llm_result

        return self._default_request(hint, period=period, focus=focus)

    def _parse_topic(self, hint: str) -> str:
        for topic_key, pattern in TOPIC_PATTERNS:
            if pattern.search(hint):
                return topic_key
        return ""

    def _parse_period(self, hint: str) -> str:
        for period_key, pattern in PERIOD_PATTERNS:
            if pattern.search(hint):
                return period_key
        return "daily"

    def _extract_focus(self, hint: str, topic: str) -> str:
        """Extract specific focus entities from hint (e.g. stock names, tech areas)."""
        cleaned = hint
        for _, pattern in TOPIC_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        for _, pattern in PERIOD_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        cleaned = re.sub(r"[帮我生成一个做份的给看下]", "", cleaned)
        cleaned = cleaned.strip()
        return cleaned if len(cleaned) >= 2 else ""

    def _resolve_preset(self, topic: str, period: str) -> str:
        """Look up preset by (topic, period). Falls back to any matching topic."""
        exact = self._topic_index.get((topic, period))
        if exact:
            return exact

        # Try the other period as fallback
        other_period = "weekly" if period == "daily" else "daily"
        fallback = self._topic_index.get((topic, other_period))
        return fallback or ""

    def _classify_with_llm(self, hint: str) -> ReportRequest | None:
        """LLM fallback for ambiguous inputs."""
        if not self._llm_config.get("api_key") and not self._has_env_key():
            return None

        try:
            from brief.llm import LLMClient
            llm = LLMClient(self._llm_config)

            preset_list = "\n".join(
                f"- {name} (topic={getattr(p, 'topic', '')}, cycle={p.cycle}): "
                f"{p.description or p.display_name}"
                for name, p in self._presets.items()
            )

            system = f"""You are an intent classifier for a report generation system.
Given a user's request, identify:
1. topic: the subject area (ai, finance, stock_a, stock_hk, stock_us, education, crypto, healthcare, energy, or other)
2. period: daily or weekly
3. preset: the best matching preset name, or empty string if none match
4. focus: any specific sub-topic or entity the user wants to focus on

Available presets:
{preset_list}

Return ONLY a JSON object:
{{"topic": "...", "period": "...", "preset": "...", "focus": "..."}}"""

            result = llm.classify(system, hint)
            clean = result.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(clean)

            preset_name = parsed.get("preset", "")
            if preset_name and preset_name not in self._presets:
                preset_name = ""

            topic = parsed.get("topic", "")
            period = parsed.get("period", "daily")

            if not preset_name and topic:
                preset_name = self._resolve_preset(topic, period)

            return ReportRequest(
                topic=topic,
                period=period,
                focus=parsed.get("focus", ""),
                raw_hint=hint,
                preset_name=preset_name or "",
                confidence=0.6,
                auto_created=not bool(preset_name),
            )
        except Exception:
            return None

    def _default_request(
        self, hint: str, period: str = "weekly", focus: str = ""
    ) -> ReportRequest:
        preset_name = "ai_daily" if period == "daily" else "ai_cv_weekly"
        return ReportRequest(
            topic="ai",
            period=period,
            focus=focus,
            raw_hint=hint,
            preset_name=preset_name,
            confidence=0.3,
        )

    @staticmethod
    def _has_env_key() -> bool:
        import os
        return bool(
            os.getenv("OPENCLAW_API_KEY")
            or os.getenv("OPENCLAW_TOKEN")
            or os.getenv("BAILIAN_API_KEY")
        )
