#!/usr/bin/env python3
"""
LunaClaw Brief — Entry point (CLI + OpenClaw Skill)

Report Agent: parses user intent (topic × period), routes to the best
preset, and runs the generation pipeline.

Usage:
  python run.py                                  # default ai_cv_weekly
  python run.py --preset stock_hk_daily          # explicit preset
  python run.py --hint "生成一个港股日报"           # auto-route by intent
  python run.py --hint "帮我做一份教育周报"         # auto-create for new topics
  python run.py --hint "看看腾讯和阿里怎么样"      # LLM-based intent routing
  python run.py --create-preset "我是新能源基金经理" # create custom preset
"""

import argparse
import sys
from pathlib import Path

import yaml

from brief.presets import get_preset, PRESETS
from brief.pipeline import ReportPipeline
from brief.intent import IntentParser
from brief.models import ReportRequest


def load_config() -> dict:
    """Merge config.yaml + config.local.yaml (local wins)."""
    root = Path(__file__).parent
    config: dict = {}

    base_path = root / "config.yaml"
    if base_path.exists():
        with open(base_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    local_path = root / "config.local.yaml"
    if local_path.exists():
        with open(local_path, "r", encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}
        _deep_merge(config, local)

    config["project_root"] = str(root)
    return config


def _deep_merge(base: dict, override: dict):
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


def _resolve_request(hint: str, explicit_preset: str, config: dict) -> ReportRequest:
    """Parse user input into a structured ReportRequest via IntentParser."""
    parser = IntentParser(PRESETS, llm_config=config.get("llm", {}))

    if explicit_preset and explicit_preset != "ai_cv_weekly":
        return parser.parse(hint, explicit_preset=explicit_preset)

    if hint:
        return parser.parse(hint)

    return parser.parse(hint, explicit_preset=explicit_preset or "ai_cv_weekly")


def _ensure_preset(request: ReportRequest, config: dict) -> str:
    """Ensure a valid preset exists for the request.

    If auto_created is True and no preset_name, dynamically create one
    via the custom preset generator.
    """
    if request.preset_name and request.preset_name in PRESETS:
        return request.preset_name

    if request.auto_created and request.topic:
        period_label = "日报" if request.period == "daily" else "周报"
        topic_labels = {
            "education": "教育", "crypto": "加密货币",
            "healthcare": "医疗健康", "energy": "新能源",
        }
        topic_label = topic_labels.get(request.topic, request.topic)
        desc = f"{topic_label}{period_label}"
        if request.focus:
            desc += f"，重点关注{request.focus}"

        print(f"🧪 未找到匹配 preset，正在为「{desc}」自动创建...")
        try:
            from brief.custom_preset import generate_custom_preset
            preset = generate_custom_preset(desc, config)
            if preset:
                print(f"✅ 已创建自定义 preset: {preset.name}")
                return preset.name
        except Exception as e:
            print(f"⚠️ 自动创建失败: {e}")

    return "ai_cv_weekly"


def generate_report(params: dict | None = None) -> dict:
    """OpenClaw Skill entry: accepts params dict, returns result dict."""
    params = params or {}
    explicit_preset = params.get("preset", "ai_cv_weekly")
    user_hint = params.get("hint", "")
    send_email = params.get("send_email", False)

    config = load_config()
    request = _resolve_request(user_hint, explicit_preset, config)
    preset_name = _ensure_preset(request, config)

    preset = get_preset(preset_name)
    pipeline = ReportPipeline(preset, config)

    focus_hint = user_hint
    if request.focus and request.focus not in (user_hint or ""):
        focus_hint = f"{user_hint}\n重点关注: {request.focus}" if user_hint else f"重点关注: {request.focus}"

    return pipeline.run(user_hint=focus_hint, send_email=send_email)


def create_custom_preset(description: str):
    """Create a custom preset from a natural language description."""
    from brief.custom_preset import generate_custom_preset
    config = load_config()
    preset = generate_custom_preset(description, config)
    if preset:
        print(f"\n✅ Custom preset '{preset.name}' created!")
        print(f"   Use: python run.py --preset {preset.name}")
    else:
        print("\n❌ Failed to create custom preset.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="LunaClaw Brief — AI-powered report agent")
    parser.add_argument(
        "--preset", default="ai_cv_weekly",
        help=f"Preset name ({' | '.join(PRESETS.keys())})",
    )
    parser.add_argument("--hint", default="", help="Natural language request (auto-routes topic & period)")
    parser.add_argument("--email", action="store_true", help="Send report via email after generation")
    parser.add_argument("--create-preset", metavar="DESC", help="Create custom preset from description")
    parser.add_argument("--debug-intent", action="store_true", help="Show intent parsing result and exit")
    args = parser.parse_args()

    if args.create_preset:
        create_custom_preset(args.create_preset)
        return

    config = load_config()
    request = _resolve_request(args.hint, args.preset, config)

    if args.debug_intent:
        print(f"📋 Intent parsing result:")
        print(f"   topic    = {request.topic}")
        print(f"   period   = {request.period}")
        print(f"   focus    = {request.focus!r}")
        print(f"   preset   = {request.preset_name!r}")
        print(f"   confidence = {request.confidence}")
        print(f"   auto_created = {request.auto_created}")
        return

    preset_name = _ensure_preset(request, config)

    if preset_name != args.preset and args.preset == "ai_cv_weekly" and args.hint:
        print(f"🧭 Intent → topic={request.topic}, period={request.period} → preset: {preset_name}")

    try:
        result = generate_report({
            "preset": preset_name,
            "hint": args.hint,
            "send_email": args.email,
        })
        if result.get("success"):
            print(f"\n🎉 报告已生成：{result.get('html_path', '')}")
        else:
            print(f"\n❌ 生成失败：{result.get('error', 'unknown')}")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 运行异常：{type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
