"""clawCat-BRIEF 总览 Demo — 一次性生成完整报告（无需 LLM API）

直接用 mock 数据跑完整个 pipeline 后半段：
  mock items → dedup → render Brief JSON → HTML → 打开浏览器

运行: python testcode/demo_full_report.py
"""

import json
import webbrowser
from datetime import datetime
from pathlib import Path

from clawcat.schema.brief import Brief, BriefItem, BriefMetadata, BriefSection, ClawComment, TimeRange
from clawcat.schema.item import Item


def build_demo_brief() -> Brief:
    """构造一份完整的模拟简报。"""
    return Brief(
        report_type="daily",
        title="AI 技术日报",
        issue_label="2026-03-28",
        time_range=TimeRange(
            user_requested="今天的AI新闻",
            resolved_start="2026-03-28T00:00:00",
            resolved_end="2026-03-28T23:59:59",
            report_generated=datetime.now().isoformat(),
            coverage_gaps=[],
        ),
        executive_summary=(
            "今日 AI 领域三大要闻：OpenAI 发布 GPT-5 引发行业震动，"
            "Meta 开源 Llama 4 推动开源生态，NVIDIA H200 供需紧张加剧 GPU 军备竞赛。"
        ),
        sections=[
            BriefSection(
                heading="头条要闻",
                section_type="hero",
                icon="🔥",
                prose="今日最重磅的消息集中在大模型发布和开源生态两个方向，值得重点关注。",
                items=[
                    BriefItem(
                        title="OpenAI 正式发布 GPT-5",
                        summary="OpenAI 在今日凌晨发布了 GPT-5 模型，在推理能力、多语言支持和代码生成方面实现了显著提升。GPT-5 采用了全新的 MoE 架构，在 MMLU 等基准测试中刷新纪录。",
                        key_facts=[
                            "参数量突破 10T（MoE 激活参数 1.5T）",
                            "MMLU 得分 92.3%，较 GPT-4o 提升 8 个百分点",
                            "推理速度提升 3 倍，延迟降至 200ms",
                            "API 定价 $15/1M tokens（输入），$60/1M tokens（输出）",
                        ],
                        verdict="技术领先但定价偏高，生态战略是关键。",
                        sources=["hackernews", "36kr", "The Verge"],
                        tags=["AI", "LLM", "GPT-5", "OpenAI"],
                    ),
                    BriefItem(
                        title="Meta 开源 Llama 4（405B）",
                        summary="Meta 发布 Llama 4 全系列开源模型，包括 8B、70B 和 405B 三个规格，均采用 Apache 2.0 许可证。405B 版本在多项基准上超越 GPT-4o。",
                        key_facts=[
                            "Apache 2.0 许可，完全可商用",
                            "405B 版本 MMLU 得分 88.6%",
                            "支持 128K 上下文窗口",
                            "已集成至 Hugging Face Transformers",
                        ],
                        verdict="开源里程碑，每个团队都值得评估。",
                        sources=["hf_papers", "hackernews"],
                        tags=["开源", "Meta", "Llama"],
                    ),
                ],
            ),
            BriefSection(
                heading="行业分析",
                section_type="analysis",
                icon="📊",
                prose="AI 基础设施投资持续升温，GPU 市场呈现寡头垄断格局。同时，AI Agent 框架竞争进入白热化阶段。",
                items=[
                    BriefItem(
                        title="NVIDIA H200 供需紧张持续",
                        summary="NVIDIA H200 GPU 交期延长至 6 个月以上，云厂商争抢产能。AMD MI300X 趁机加速渗透。",
                        key_facts=[
                            "H200 现货价格上涨 20%",
                            "微软、Google 联合采购 100 万颗 H200",
                            "AMD MI300X 拿下 AWS 新订单",
                        ],
                        verdict="GPU 军备竞赛加剧，AMD 是最大变量。",
                        sources=["wallstreetcn", "cn_economy"],
                        tags=["GPU", "NVIDIA", "AMD"],
                    ),
                    BriefItem(
                        title="LangGraph vs CrewAI vs AutoGen：Agent 框架之争",
                        summary="LangChain 团队发布 LangGraph v0.3，新增 multi-agent orchestration 和 human-in-the-loop 支持。CrewAI 和 AutoGen 也在快速迭代。",
                        key_facts=[
                            "LangGraph v0.3 支持 sub-graph 和 map-reduce",
                            "CrewAI 获得 $18M A 轮融资",
                            "AutoGen v0.4 重写了核心架构",
                        ],
                        verdict="框架混战期，选 LangGraph 最稳。",
                        sources=["hackernews", "github_trending"],
                        tags=["Agent", "LangGraph", "框架"],
                    ),
                ],
            ),
            BriefSection(
                heading="开源速递",
                section_type="items",
                icon="📦",
                prose="本周 GitHub Trending 上值得关注的 AI 项目。",
                items=[
                    BriefItem(
                        title="browser-use/browser-use",
                        summary="让 AI Agent 操控浏览器的框架，支持 Playwright + LLM 驱动的自动化测试和数据采集。",
                        key_facts=["⭐ 12.3K stars", "支持 GPT-4o / Claude 3.5 / Gemini"],
                        verdict="浏览器自动化的新范式，值得关注。",
                        sources=["github_trending"],
                        tags=["Agent", "Browser", "自动化"],
                    ),
                    BriefItem(
                        title="instructor-ai/instructor",
                        summary="结构化 LLM 输出框架，通过 Pydantic 模型约束 LLM 生成格式，支持自动重试和校验。",
                        key_facts=["⭐ 8.5K stars", "支持 OpenAI / Anthropic / Ollama"],
                        verdict="LLM 结构化输出的事实标准。",
                        sources=["github_trending"],
                        tags=["结构化输出", "Pydantic"],
                    ),
                ],
            ),
            BriefSection(
                heading="Claw 锐评",
                section_type="review",
                icon="🦞",
                prose="本期锐评聚焦 AI 行业的三个核心矛盾。",
                items=[
                    BriefItem(
                        title="开源 vs 闭源：谁在赢？",
                        summary="Llama 4 的发布让「开源够用」成为共识，但 GPT-5 的能力上限仍然让闭源保持领先一步。",
                        key_facts=["开源模型在 MMLU 上追平闭源", "闭源在 Agent/Tool Use 上仍有 5-10 分优势"],
                        claw_comment=ClawComment(
                            highlight="开源不是要打败闭源，而是要让「90% 的场景不需要闭源」。这才是 Meta 的真正策略。",
                            concerns=["开源模型的安全对齐仍是隐患", "中小团队的微调成本被低估了"],
                            verdict="企业选型：先评估场景复杂度，再决定开源/闭源。别跟风。",
                        ),
                        sources=["36kr", "hackernews"],
                        tags=["开源", "闭源", "选型"],
                    ),
                    BriefItem(
                        title="AI 泡沫论：这次不一样？",
                        summary="高盛报告指出 AI 投资回报率仍低于预期，但微软、Google 表示将继续加大资本开支。",
                        key_facts=["2025 年全球 AI 投资超 $2000 亿", "仅 10% 的 AI 项目产生了正 ROI"],
                        claw_comment=ClawComment(
                            highlight="泡沫不泡沫不重要，重要的是你在泡沫中学到了什么。",
                            concerns=["大量 AI Wrapper 公司将在 2026 年消亡", "基础设施过度建设的风险"],
                            verdict="真正的 AI 价值在「降本增效」而非「创造新需求」。活下来的都是解决真问题的。",
                        ),
                        sources=["wallstreetcn", "cn_economy"],
                        tags=["泡沫", "投资", "趋势"],
                    ),
                ],
            ),
        ],
        metadata=BriefMetadata(
            llm_model="kimi-k2.5",
            llm_calls=8,
            prompt_tokens=15000,
            completion_tokens=8000,
            sources_used=["hackernews", "36kr", "hf_papers", "wallstreetcn",
                          "github_trending", "cn_economy"],
            items_fetched=67,
            items_selected=18,
            generation_seconds=42.3,
        ),
    )


def run_demo():
    print("=" * 60)
    print("  🦞 clawCat-BRIEF 总览 Demo")
    print("=" * 60)

    # 1. Build mock brief
    print("\n[1/4] 构造 Brief 对象...")
    brief = build_demo_brief()
    print(f"      标题: {brief.title}")
    print(f"      期号: {brief.issue_label}")
    print(f"      章节: {len(brief.sections)} 个")
    total_items = sum(len(s.items) for s in brief.sections)
    print(f"      条目: {total_items} 条")

    # 2. Run grounding checks
    print("\n[2/4] 执行 Grounding 校验...")
    from clawcat.grounding.consistency import ConsistencyChecker
    from clawcat.grounding.coverage import CoverageChecker
    from clawcat.grounding.structure import StructureGrounder

    brief_json = brief.model_dump_json()
    checkers = [
        ("StructureGrounder", StructureGrounder()),
        ("ConsistencyChecker", ConsistencyChecker()),
        ("CoverageChecker", CoverageChecker(
            expected_sections=[s.heading for s in brief.sections]
        )),
    ]
    for name, checker in checkers:
        result = checker.check(brief_json, [])
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"      {name}: {status} (score={result.score:.2f}, issues={len(result.issues)})")

    # 3. Render HTML
    print("\n[3/4] 渲染 HTML...")
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    template_dir = Path("clawcat/templates")
    static_dir = Path("clawcat/static")
    output_dir = Path("output/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader([str(template_dir), str(static_dir)]),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html")

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
        brand_full_name="clawCat-BRIEF",
        brand_tagline="AI-Powered Report Engine",
        brand_author="by llx & Luna",
    )

    html_path = output_dir / "demo_ai_daily.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"      HTML: {html_path}")

    # 4. Save JSON
    print("\n[4/4] 保存 Brief JSON...")
    json_path = output_dir / "demo_ai_daily.json"
    json_path.write_text(
        json.dumps(brief_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"      JSON: {json_path}")

    # Summary
    print("\n" + "=" * 60)
    print("  ✅ Demo 完成！")
    print(f"  📄 HTML: {html_path.resolve()}")
    print(f"  📦 JSON: {json_path.resolve()}")
    print("=" * 60)

    # Open in browser
    try:
        webbrowser.open(str(html_path.resolve()))
        print("\n  🌐 已在浏览器中打开报告")
    except Exception:
        print("\n  💡 请手动打开 HTML 文件查看效果")


if __name__ == "__main__":
    run_demo()
