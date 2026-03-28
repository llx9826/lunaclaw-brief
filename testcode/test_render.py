"""Tests for Jinja2 rendering with Brief JSON data."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from clawcat.schema.brief import Brief, BriefItem, BriefMetadata, BriefSection, ClawComment, TimeRange


def _make_brief() -> Brief:
    return Brief(
        report_type="daily",
        title="AI 技术日报",
        issue_label="2026-03-28",
        time_range=TimeRange(
            user_requested="今天",
            resolved_start="2026-03-28T00:00:00",
            resolved_end="2026-03-28T23:59:59",
            report_generated="2026-03-28T15:00:00",
        ),
        executive_summary="今日 AI 领域发生了若干重要事件，GPT-5 发布引起广泛关注。",
        sections=[
            BriefSection(
                heading="🔥 头条要闻",
                section_type="hero",
                icon="🔥",
                prose="今日最重磅的消息集中在大模型和开源生态。",
                items=[
                    BriefItem(
                        title="OpenAI 发布 GPT-5",
                        summary="OpenAI 正式发布 GPT-5，性能提升 10 倍。",
                        key_facts=["参数量突破 10T", "推理速度提升 3x", "支持 100+ 语言"],
                        verdict="技术领先但定价偏高。",
                        sources=["hackernews", "36kr"],
                        tags=["AI", "LLM", "GPT"],
                    ),
                    BriefItem(
                        title="Meta 开源 Llama 4",
                        summary="Meta 开源 Llama 4 模型，可商用。",
                        key_facts=["Apache 2.0 许可", "405B 参数"],
                        verdict="开源里程碑。",
                        sources=["hf_papers"],
                        tags=["开源", "Meta"],
                    ),
                ],
            ),
            BriefSection(
                heading="📊 行业分析",
                section_type="analysis",
                icon="📊",
                prose="AI 基础设施投资持续升温。",
                items=[
                    BriefItem(
                        title="GPU 市场供需紧张",
                        summary="NVIDIA H200 供不应求，交期延长至 6 个月。",
                        key_facts=["H200 价格上涨 20%", "AMD MI300X 加速追赶"],
                        verdict="GPU 军备竞赛加剧。",
                        sources=["wallstreetcn"],
                        tags=["GPU", "NVIDIA"],
                    ),
                ],
            ),
            BriefSection(
                heading="🦞 Claw 锐评",
                section_type="review",
                icon="🦞",
                prose="本期锐评聚焦大模型军备竞赛。",
                items=[
                    BriefItem(
                        title="大模型价格战",
                        summary="各家大模型纷纷降价，市场进入红海竞争。",
                        key_facts=["GPT-4o 降价 50%", "Claude 3.5 免费额度翻倍"],
                        claw_comment=ClawComment(
                            highlight="降价不等于降质，但用户更关注的是稳定性和合规性。",
                            concerns=["免费策略能维持多久？", "中小厂商会被挤出市场"],
                            verdict="短期利好用户，长期洗牌不可避免。",
                        ),
                        sources=["36kr", "wallstreetcn"],
                        tags=["价格战", "竞争"],
                    ),
                ],
            ),
        ],
        metadata=BriefMetadata(
            llm_model="kimi-k2.5",
            sources_used=["hackernews", "36kr", "hf_papers", "wallstreetcn"],
            items_fetched=45,
            items_selected=15,
            generation_seconds=23.5,
        ),
    )


def test_render_html():
    """Render a complete Brief to HTML and verify output."""
    template_dir = Path("clawcat/templates")
    static_dir = Path("clawcat/static")

    if not template_dir.exists():
        print("    Templates not found, skipping")
        return

    env = Environment(
        loader=FileSystemLoader([str(template_dir), str(static_dir)]),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html")

    brief = _make_brief()
    brief_data = brief.model_dump()

    html = template.render(
        brief=brief_data,
        title=brief.title,
        issue_label=brief.issue_label,
        time_range=brief_data["time_range"],
        sections=brief_data["sections"],
        executive_summary=brief.executive_summary,
        metadata=brief_data["metadata"],
        generated_at="2026-03-28 15:00",
        luna_logo_b64="",
        brand_full_name="clawCat-BRIEF",
        brand_tagline="AI-Powered Report Engine",
        brand_author="by llx & Luna",
    )

    assert "AI 技术日报" in html
    assert "GPT-5" in html
    assert "Claw 锐评" in html
    assert "hackernews" in html

    output_dir = Path("output/render_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "test_brief_render.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"    Rendered: {out_path}")

    json_path = output_dir / "test_brief.json"
    import json
    json_path.write_text(
        json.dumps(brief_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"    JSON: {json_path}")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
    print(f"\nRan {len(tests)} render tests: {passed} passed, {failed} failed")
