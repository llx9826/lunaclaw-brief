# 🦞 LunaClaw Brief — OpenClaw Skill

**Pluggable AI-Powered Report Engine** | 插件化 AI 智能简报引擎

## Overview / 概述

LunaClaw Brief is an OpenClaw Skill that generates intelligent reports across multiple domains. It features a plugin architecture with 8-stage pipeline, 8 data sources, 7 editor strategies, hybrid intent routing, streaming output, and multi-channel delivery.

LunaClaw Brief 是一个 OpenClaw Skill，支持多领域智能报告生成。采用插件化架构，8 阶段管线，8 个数据源，7 种编辑器策略，混合意图路由，流式输出，多渠道推送。

## Presets / 预设

| Preset | Type | Description |
|--------|------|-------------|
| `ai_cv_weekly` | Tech | AI/CV/多模态技术深度周报 |
| `ai_daily` | Tech | AI 技术日报 |
| `finance_weekly` | Finance | 金融投资周报 |
| `finance_daily` | Finance | 金融快报日刊 |
| `stock_a_daily` | Stock | A 股日报（大盘/板块/北向资金/IPO/异动） |
| `stock_hk_daily` | Stock | 港股日报（恒生/南向资金/中概股/IPO） |
| `stock_us_daily` | Stock | 美股日报（S&P/NASDAQ/科技巨头/IPO） |
| Custom | Any | via `--create-preset` natural language |

## Data Sources / 数据源

| Source | Coverage |
|--------|----------|
| `github` | Open-source projects + competitor discovery |
| `arxiv` | Academic papers |
| `hackernews` | Tech community discussions |
| `paperswithcode` | ML papers with code |
| `finnews` | Financial news (HN + BBC/NYT RSS) |
| `yahoo_finance` | Yahoo Finance RSS + market indices |
| `eastmoney` | 东方财富 (A-share news, IPO calendar) |
| `xueqiu` | 雪球 (hot stocks, sentiment) |

## Usage / 使用方式

### Via CLI

```bash
python run.py                                    # AI/CV Weekly (default)
python run.py --preset stock_a_daily             # A-share daily
python run.py --hint "今天A股怎么样"               # Auto-route → stock_a_daily
python run.py --hint "帮我看看腾讯和阿里"          # LLM auto-route
python run.py --preset ai_cv_weekly --email      # Generate + email
python run.py --create-preset "我是新能源基金经理"  # Create custom preset
python -m brief.scheduler                        # Run scheduled jobs
```

### Via OpenClaw Skill API

```python
from run import generate_report

result = generate_report({
    "preset": "stock_hk_daily",
    "hint": "重点关注腾讯和美团",
    "send_email": True,
})
```

### Trigger Phrases / 触发短语

- "生成周报" / "生成日报" / "generate weekly/daily"
- "生成金融周报/日报" / "generate finance report"
- "生成A股/港股/美股日报" / "generate A-share/HK/US brief"

## Key Capabilities / 核心能力

- **Hybrid Intent Router**: Regex (instant) + LLM classification (fallback) for preset routing
- **Unified Markdown Schema**: `## Section` → `### N. Item` → `**Label**:` → `**🦞 Claw**:` structure
- **Streaming Output**: `pipeline.run_stream()` yields progress events + content chunks
- **Multi-Channel Delivery**: Email (SMTP), Webhook (Slack/DingTalk/Feishu/custom)
- **Cron Scheduler**: Auto-generate reports on schedule with multi-channel push
- **Custom Presets**: Create domain-specific presets via natural language
- **Quality Control**: Auto-check structure/word count, retry if below threshold
- **Three-Level Memory**: Pluggable `MemoryStore` protocol with preset-scoped dedup:
  - L1 `ItemStore` — item-id dedup (same article won't reuse)
  - L2 `TopicStore` — keyword fingerprint diversity (same theme won't repeat)
  - L3 `ContentStore` — claim extraction + negative constraint injection (same viewpoint won't appear in reviews)

## Architecture / 架构

| Pattern | Where |
|---------|-------|
| Adapter | `BaseSource` → 8 source adapters |
| Strategy | `BaseEditor` → 7 editor strategies |
| Pipeline | 8-stage `ReportPipeline` (sync + stream) |
| Registry | `@register_source` / `@register_editor` decorators |
| Observer | `MiddlewareChain` for timing, metrics, custom hooks |
| Factory | `create_sources()` / `create_editor()` |
| Cache | `FileCache` with TTL for API responses |
| Protocol | `MemoryStore` → ItemStore / TopicStore / ContentStore |
| Facade | `MemoryManager` composes pluggable memory backends |

## Configuration / 配置

Global config in `config.yaml`. Secrets in `config.local.yaml` (gitignored).

```yaml
# config.local.yaml (not committed)
llm:
  api_key: "your-key"
```

Auto-detects OpenClaw environment (`OPENCLAW_API_KEY` / `OPENCLAW_BASE_URL`) — no manual LLM config needed when running as an OpenClaw skill.

## Output / 输出

- **HTML**: Self-contained dark-theme report with embedded Luna logo
- **Markdown**: Raw LLM output
- **PDF**: Via WeasyPrint (optional)
- **Email**: HTML body + PDF attachment
- **Webhook**: Slack/DingTalk/Feishu/custom HTTP POST

---

*Built by llx & Luna 🐱 — where the claw meets the code.* 🦞
