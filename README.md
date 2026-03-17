<p align="center">
  <img src="static/luna_logo_wordmark.png" alt="LunaClaw Brief" width="420">
</p>

<p align="center">
  <strong>Pluggable AI-Powered Report Engine</strong> | 插件化 AI 智能简报引擎
</p>

<p align="center">
  Built with ❤️ by <strong>llx</strong> & <strong>Luna</strong> 🐱 (a brown tabby Maine Coon)
</p>

---

## What is LunaClaw Brief?

LunaClaw Brief is an extensible report generation engine that fetches content from multiple sources, scores and selects the most relevant items, generates opinionated reports via LLM, and renders them into beautiful HTML/PDF with multi-channel delivery.

LunaClaw Brief 是一个可扩展的报告生成引擎，从多个数据源抓取内容，通过多维打分选材，由 LLM 生成有观点的深度报告，渲染为精美的 HTML/PDF 并支持多渠道推送。

## Architecture / 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                       ReportPipeline                              │
│  ┌───────┐  ┌───────┐  ┌────────┐  ┌─────────┐  ┌───────────┐  │
│  │ Fetch │→│ Score │→│ Select │→│ Memory  │→│ Edit (LLM)│  │
│  │(async)│  │(multi)│  │(Top-K) │  │ Dedup   │  │ stream/sync│  │
│  └───────┘  └───────┘  └────────┘  └─────────┘  └───────────┘  │
│                                       ↕                ↕         │
│                              ┌─────────────────────────────┐     │
│                              │      MemoryManager          │     │
│                              │  L1 ItemStore   (item dedup)│     │
│                              │  L2 TopicStore  (theme div) │     │
│                              │  L3 ContentStore(claim neg) │     │
│                              └─────────────────────────────┘     │
│       ↓                                              ↓           │
│  ┌─────────────┐                           ┌─────────────────┐  │
│  │   Quality   │←─────────────────────────│  Render (Jinja2 │  │
│  │   Checker   │                           │  + WeasyPrint)  │  │
│  └─────────────┘                           └─────────────────┘  │
│       ↓                                              ↓           │
│  ┌─────────────┐                           ┌─────────────────┐  │
│  │    Retry    │                           │  Email/Webhook  │  │
│  │  (if <70%)  │                           │   Delivery      │  │
│  └─────────────┘                           └─────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│  MiddlewareChain: Timing · Metrics · Custom Hooks                 │
│  BriefLogger: Structured logging with phase context               │
│  Scheduler: Cron-based auto-generation + multi-channel push       │
└──────────────────────────────────────────────────────────────────┘
```

## Design Patterns / 设计模式

| Pattern | Application | 应用 |
|---------|-------------|------|
| **Adapter** | `BaseSource` → GitHub / arXiv / HN / PwC / FinNews / Yahoo Finance / Eastmoney / Xueqiu | 8 个数据源统一接口 |
| **Strategy** | `BaseEditor` → Weekly / Daily / Finance / Stock (A/HK/US) | 7 种 LLM prompt 策略 |
| **Pipeline** | `ReportPipeline` — 8-stage flow (sync + streaming) | 8 阶段管线 |
| **Registry** | `@register_source` / `@register_editor` decorators | 装饰器零配置注册 |
| **Observer** | `MiddlewareChain` + `PipelineMiddleware` | 管线钩子系统 |
| **Factory** | `create_sources()` / `create_editor()` | 工厂函数动态创建 |
| **Dataclass** | `Item` / `ScoredItem` / `PresetConfig` / `ReportDraft` | 强类型数据模型 |
| **Cache** | `FileCache` with TTL | 文件级 TTL 缓存 |
| **Protocol** | `MemoryStore` → ItemStore / TopicStore / ContentStore | 三级记忆协议 |
| **Facade** | `MemoryManager` composes pluggable memory stores | 记忆门面模式 |

## Presets / 预设报告类型

| Preset | Description | Sources | Editor |
|--------|-------------|---------|--------|
| `ai_cv_weekly` | AI/CV tech deep-dive weekly | GitHub, arXiv, HN, PwC | tech_weekly |
| `ai_daily` | AI tech daily brief | GitHub, arXiv, HN | tech_daily |
| `finance_weekly` | Investment market weekly | FinNews, HN, Yahoo Finance | finance_weekly |
| `finance_daily` | Market flash daily | FinNews, HN, Yahoo Finance | finance_daily |
| `stock_a_daily` | A-share market daily (A股日报) | Eastmoney, Xueqiu, FinNews | stock_a |
| `stock_hk_daily` | HK stock market daily (港股日报) | FinNews, Yahoo Finance, Xueqiu | stock_hk |
| `stock_us_daily` | US stock market daily (美股日报) | Yahoo Finance, FinNews | stock_us |

Custom presets can be created via natural language: `python run.py --create-preset "我是新能源基金经理"`

## Quick Start / 快速开始

```bash
# Install dependencies
pip install -r requirements.txt

# Configure LLM key (create config.local.yaml, gitignored)
cat > config.local.yaml << 'EOF'
llm:
  api_key: "your-api-key-here"
EOF

# Generate AI/CV Weekly (default)
python run.py

# Generate with auto-routing from hint
python run.py --hint "今天A股怎么样"         # → stock_a_daily
python run.py --hint "生成港股日报"           # → stock_hk_daily
python run.py --hint "帮我看看腾讯和阿里"    # → LLM auto-route

# Explicit preset
python run.py --preset stock_us_daily

# Generate and send via email
python run.py --preset ai_cv_weekly --email

# Create custom preset from natural language
python run.py --create-preset "我是半导体行业分析师，关注芯片设计和晶圆代工"

# Run scheduler (cron-based auto-generation)
python -m brief.scheduler
```

## Key Features / 核心特性

### Three-Level Memory System / 三级记忆系统

Pluggable memory architecture that prevents content repetition across issues:

| Level | Store | Granularity | Effect |
|-------|-------|-------------|--------|
| L1 | `ItemStore` | item_id (SHA-256) | Same article/repo won't be reused |
| L2 | `TopicStore` | keyword fingerprint (Jaccard) | Same theme won't repeat consecutively |
| L3 | `ContentStore` | LLM-extracted claims | Same viewpoint won't appear in reviews |

All stores implement the `MemoryStore` protocol and are composed by `MemoryManager` — fully pluggable and preset-scoped.

```python
from brief.memory import MemoryManager

manager = MemoryManager.create_default(data_dir, llm=llm_client)
filtered = manager.filter_items(items, "ai_weekly", window_days=30)
memories = manager.recall_all("ai_weekly")
manager.save_all("ai_weekly", "2026-03-17", items, markdown)
```

### Unified Markdown Schema

All editors use a standardized Markdown schema for consistent rendering:

```markdown
## Section Title
### 1. Item Title
**Label**：structured value
**🦞 Claw 锐评**：opinionated review
```

### Hybrid Intent Router

User hints are automatically routed to the correct preset:
- **Regex** (instant, free): patterns like "A股", "港股", "美股", "weekly"
- **LLM** (fallback): ambiguous queries like "帮我看看腾讯今天怎么样"

### Multi-Channel Delivery

- **Email**: HTML body + PDF attachment via SMTP
- **Webhook**: Slack, DingTalk (钉钉), Feishu (飞书), custom HTTP
- **Scheduler**: Cron-based auto-generation and push

### Streaming Output

```python
for event in pipeline.run_stream(user_hint="..."):
    if event["type"] == "chunk":
        print(event["content"], end="")
```

## Project Structure / 项目结构

```
lunaclaw-brief/
├── brief/                          # Core engine / 核心引擎
│   ├── models.py                   # Data models (Item, ScoredItem, PresetConfig...)
│   ├── presets.py                  # 7 built-in presets + custom preset loader
│   ├── pipeline.py                 # 8-stage ReportPipeline (sync + stream)
│   ├── registry.py                 # Plugin Registry (@register_source/editor)
│   ├── middleware.py               # Pipeline hooks (Timing, Metrics, Custom)
│   ├── log.py                      # Structured logging with context binding
│   ├── cache.py                    # File-based TTL cache
│   ├── scoring.py                  # Multi-dimensional Scorer + Selector
│   ├── quality.py                  # LLM output QualityChecker
│   ├── llm.py                      # LLM client (chat/classify/stream + usage tracking)
│   ├── sender.py                   # Email + Webhook delivery
│   ├── scheduler.py                # Cron-based scheduler
│   ├── custom_preset.py            # LLM-based custom preset generator
│   ├── memory/                     # Three-level pluggable memory system
│   │   ├── protocol.py             #   MemoryStore abstract protocol
│   │   ├── item_store.py           #   L1: item-id dedup (preset-scoped)
│   │   ├── topic_store.py          #   L2: topic fingerprint diversity
│   │   ├── content_store.py        #   L3: claim extraction + neg constraints
│   │   └── manager.py              #   MemoryManager facade
│   ├── sources/                    # Data source adapters (8 sources)
│   │   ├── base.py                 #   BaseSource (abstract)
│   │   ├── github.py               #   GitHub (with competitor discovery)
│   │   ├── arxiv.py                #   arXiv papers
│   │   ├── hackernews.py           #   Hacker News
│   │   ├── paperswithcode.py       #   Papers with Code
│   │   ├── finnews.py              #   Financial news (HN + RSS)
│   │   ├── yahoo_finance.py        #   Yahoo Finance RSS
│   │   ├── eastmoney.py            #   Eastmoney (东方财富)
│   │   └── xueqiu.py               #   Xueqiu (雪球)
│   ├── editors/                    # LLM editor strategies (7 editors)
│   │   ├── base.py                 #   BaseEditor (retry + stream)
│   │   ├── weekly.py               #   Tech weekly
│   │   ├── daily.py                #   Tech daily
│   │   ├── finance.py              #   Finance weekly + daily
│   │   └── stock.py                #   A-share / HK / US stock
│   └── renderer/                   # Rendering layer
│       ├── markdown_parser.py      #   Markdown → structured HTML (kv-row, claw-card)
│       └── jinja2.py               #   Jinja2 + WeasyPrint PDF
├── templates/                      # Jinja2 templates
│   ├── base.html                   #   Base layout (with Luna logo)
│   └── report.html                 #   Unified report template
├── static/                         # Static assets
│   ├── style.css                   #   Design system (dark theme + print)
│   └── luna_logo*.png              #   Luna mascot logo
├── run.py                          # CLI + OpenClaw Skill entry point
├── config.yaml                     # Global config (non-secret)
├── skill.yaml                      # OpenClaw Skill definition
├── requirements.txt                # Python dependencies
└── SKILL.md                        # Skill documentation
```

## Extending / 扩展指南

### Add a new data source / 新增数据源

```python
# brief/sources/my_source.py
from brief.sources.base import BaseSource
from brief.registry import register_source

@register_source("my_source")
class MySource(BaseSource):
    name = "my_source"

    async def fetch(self, since, until) -> list[Item]:
        ...
```

### Create custom preset via CLI / 命令行创建自定义预设

```bash
python run.py --create-preset "我是新能源基金经理，每天关注光伏、锂电、风电板块"
# → Generates data/custom_presets/new_energy_daily.yaml
# → Available as: python run.py --preset new_energy_daily
```

### Add a custom middleware / 自定义中间件

```python
from brief.middleware import PipelineMiddleware, PipelineContext

class SlackNotifyMiddleware(PipelineMiddleware):
    def on_pipeline_end(self, ctx: PipelineContext):
        send_slack(f"Report {ctx.issue_label} generated in {ctx.elapsed:.0f}s")

pipeline.use(SlackNotifyMiddleware())
```

### Schedule auto-generation / 配置定时生成

```yaml
# config.yaml
schedule:
  - preset: stock_a_daily
    cron: "0 18 * * 1-5"
    delivery:
      - type: email
      - type: webhook
        url: "https://hooks.slack.com/..."
        webhook_type: slack
```

## Tech Stack / 技术栈

- **Python 3.10+** — async/await, dataclasses, type hints
- **aiohttp** — async HTTP for parallel source fetching
- **Jinja2** — template rendering
- **WeasyPrint** — HTML → PDF (optional)
- **OpenAI-compatible API** — LLM content generation (auto-detects OpenClaw)

## License

MIT

---

*LunaClaw Brief — where Luna holds the claws, and the claws hold the truth.* 🦞🐱
