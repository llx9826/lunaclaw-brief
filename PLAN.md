# ClawCat Brief — 完整技术方案

## 1. 项目定位

**一句话**：AI 驱动的任意题材简报引擎——Planner 自动理解需求、动态选源、多步生成、结构化校验、HTML/PDF 交付。

**核心价值不是「调 LLM 写文字」，而是生成之后的质量闭环**：

- 4 维 grounding 检测（时间 / 实体 / 数值 / 结构）
- 章节级自动重试
- 全文一致性检查
- 降级替换不可验证数据

**对外统一叙事**：端到端简报引擎（非「瘦渲染 skill」）。Codex 里的 clawCat SKILL.md 定义的是 skill 接口协议；本仓库是完整的宿主侧实现。

---

## 2. 架构总览

```
用户输入 ("做个每日AI新闻")
    ↓
┌─────────────────────────────────────┐
│ 1. Planner Agent                    │
│    读 registry.json + UserProfile   │
│    → 输出 TaskConfig (Pydantic)     │
└──────────────┬──────────────────────┘
               ↓ TaskConfig
┌─────────────────────────────────────┐
│ 2. Fetch (动态加载 adapters)        │
│    传入 since/until                 │
│    → 输出 list[Item]               │
└──────────────┬──────────────────────┘
               ↓ list[Item]
┌─────────────────────────────────────┐
│ 3. 时间硬过滤 + LangMem 去重       │
│    → 输出 list[Item] (干净)         │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 4. LLM 选材 (instructor)           │
│    → 输出 SelectedItems             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 5. Map (并行摘要)                   │
│ 6. Plan (大纲生成)                  │
│ 7. Write (按节并行, fan-out)        │
│ 8. Check (章节级 grounding)         │
│    → fail: 重写该章节               │
│ 9. Assemble + Polish (一致性检查)   │
│    → pass: 继续                     │
│    → degrade: 替换不可验证数据      │
│    → block: 拒绝发布                │
│    全部由 LangGraph StateGraph 编排  │
└──────────────┬──────────────────────┘
               ↓ Brief (Pydantic JSON)
┌─────────────────────────────────────┐
│ 10. Render (Jinja2 → HTML)          │
│ 11. Export (Playwright → PDF)       │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 12. Save (LangMem 记录本期条目)     │
└─────────────────────────────────────┘
```

**六层，每层通过一种数据格式通信**：

- 输入 → 规划：用户文本 + UserProfile + registry.json
- 规划 → 数据：`TaskConfig`
- 数据 → 生成：`list[Item]`
- 生成内部：`Brief` (Pydantic, 层间唯一合约)
- 生成 → 渲染：`Brief.model_dump()` (JSON dict)
- 渲染输出：HTML + PDF 文件

---

## 3. Brief Schema（层间合约）

LLM 不再输出自由 Markdown，而是输出 Pydantic 结构化对象。渲染层只接收这个 schema。

```python
class ClawComment(BaseModel):
    highlight: str
    concerns: list[str]
    verdict: str

class BriefItem(BaseModel):
    title: str
    summary: str
    key_facts: list[str]
    claw_comment: ClawComment | None = None
    sources: list[str] = []
    tags: list[str] = []

class BriefSection(BaseModel):
    heading: str
    section_type: str   # "hero" | "analysis" | "items" | "strategy" | "review"
    icon: str = ""
    prose: str = ""
    items: list[BriefItem] = []

class TimeRange(BaseModel):
    user_requested: str
    resolved_start: str
    resolved_end: str
    report_generated: str
    coverage_gaps: list[str] = []

class Brief(BaseModel):
    schema_version: str = "1.0"
    report_type: str
    title: str
    issue_label: str
    time_range: TimeRange
    executive_summary: str
    sections: list[BriefSection]
    metadata: BriefMetadata
```

**上游（生成层）的唯一输出目标；下游（渲染层）的唯一输入来源。**

---

## 4. 组件选型

### 引入的成熟组件

| 组件 | 替代什么 | 用途 |
|------|---------|------|
| **LangGraph** | pipeline.py 700 行 | StateGraph + Send fan-out + 条件边 + retry policy |
| **LangChain ChatOpenAI** | llm.py 200 行 | base_url 兼容百炼/OpenClaw + streaming + usage |
| **instructor** | 手写 retry + f-string prompt | 结构化输出 + Pydantic 校验 + 自动重试 |
| **Pydantic v2** | dataclass models | Brief schema + 字段校验 + JSON 序列化 |
| **pydantic-settings** | 手写 yaml merge | 配置管理（yaml + env + .env） |
| **LangMem** | 手写 ItemStore/TopicStore JSON | 条目级精确去重 + 语义去重 + 持久化 |
| **feedparser** | 130 行手写 XML 解析 | RSS/Atom 解析 |
| **Playwright** | WeasyPrint | HTML → PDF（更快、CSS 兼容性更好） |
| **LangSmith** | observability.py 160 行 | 自动 trace 每个节点 |

### 保留的自写部分

| 保留 | 理由 |
|------|------|
| grounding checkers | 领域专用业务逻辑（时间/实体/数值/结构） |
| adapters/ 取数代码 | copy 自 ClawHub 优秀 skill，本地统一管理 |
| prompts/ 模板 | 各场景的 system/user prompt |
| Jinja2 HTML 模板 | 渲染层模板 |

### 删除的代码

scoring/、eval/、citation.py、token_budget.py、custom_preset.py、
quality.py、sanitizer.py、observability.py、markdown_parser.py (370 行)、
llm.py、pipeline.py 的编排逻辑、gate.py 的循环逻辑

---

## 5. 数据源管理

### 原则

- 数据源代码 **copy 到本地** 统一管理，不运行时依赖外部 skill
- 每个 adapter 20-50 行，只做取数，输出统一 `FetchResult`
- `registry.json` 声明每个源的能力，Planner Agent 读它来选源

### 本地 adapter 统一接口

```python
class FetchResult(BaseModel):
    source: str
    items: list[Item]
    fetched_at: str
    time_filtered: bool = False

async def fetch(since: datetime, until: datetime, config: dict = {}) -> FetchResult:
    ...
```

### registry.json 结构

每个源声明：name、module、domains、language、china_accessible、
requires_key、time_filterable、provides、description、best_for。

Planner Agent 将 registry.json + 用户输入 → instructor 结构化输出 → `SourceSelection`。

### 第一批 adapter（来源）

| Adapter | Copy 自 | 覆盖 |
|---------|---------|------|
| hackernews | news-aggregator-skill | 全球科技新闻 |
| 36kr | news-aggregator-skill | 中国科技/创投 |
| wallstreetcn | news-aggregator-skill | 金融/宏观 |
| weibo | news-aggregator-skill | 社交热点 |
| tencent | news-aggregator-skill | 综合新闻 |
| v2ex | news-aggregator-skill | 开发者社区 |
| github_trending | news-aggregator-skill | 开源项目 |
| hf_papers | news-aggregator-skill | AI 论文 |
| cn_economy | cn-economy-news skill | 官方经济资讯 |
| akshare_stock | akshare-finance skill | A股/港股/美股行情 |
| akshare_macro | akshare-cn-market skill | 宏观数据 |
| rss | 自写（feedparser） | 通用 RSS/Atom |
| arxiv | 现有代码保留 | 学术论文 |

---

## 6. 新鲜度约束（五层保障）

**周报只讲这周，日报只讲今天——硬约束，不是建议。**

1. **Adapter 层**：传入 since/until，源端过滤或本地过滤
2. **Pipeline 硬过滤**：无 published_at 的条目直接丢弃
3. **Prompt 层**：注入明确时间约束指令
4. **Report 层**：Brief.time_range 展示三个时间（用户请求/实际/生成）
5. **Check 层**：TemporalGrounder 检查报告中日期是否在范围内

补充：素材不足时可 Smart Fill（扩大范围），但必须标记 `is_supplementary`。

---

## 7. 去重（LangMem 三层）

1. **精确去重**：item_id (SHA256) 匹配 → 跳过
2. **语义去重**：LangMem 向量搜索，相似度 > 0.85 → 标记近似重复
3. **话题衰减**：同一话题连续 N 期出现 → 降权

每期结束后，把使用的条目写入 LangMem，供下次去重。

---

## 8. 素材选取（LLM 选材）

不用 BM25/MMR 打分。由 LLM 从去重后的 items 中挑选最值得报道的条目。

通过 instructor 输出 `SelectedItems`，每条包含：item_index、reason、priority、suggested_section。

---

## 9. 多步生成（Map-Plan-Write）

**不再一次 LLM 调用生成整篇报告。**

| 步骤 | 做什么 | 每次输入规模 |
|------|--------|-------------|
| Map | 5 条一批并行摘要 | ~2K tokens |
| Plan | 所有摘要 → 大纲 JSON | ~3K tokens |
| Write | 每节独立生成 BriefSection | ~3K tokens |
| Check | 每节 grounding 检查 | 规则检查 |
| Polish | 全文一致性修正 | ~8K tokens |

每步认知负荷低，失败只重做该步。

借鉴 Open Deep Research 的 Supervisor-Researcher 模式 +
GPT-Researcher 的 Researcher-Reviewer-Reviser 子图模式。

---

## 10. 校验（Grounding + Gate）

### 章节级检查（Write 后立即跑）

- TemporalGrounder：日期在合理范围内
- EntityGrounder：实体名出现在源数据中
- FactTableGrounder：数值可溯源到事实表
- StructureGrounder：Claw 锐评数量达标

### 全文级检查（Assemble 后跑）

- ConsistencyChecker（新增）：跨节矛盾、重复论述
- CoverageChecker（新增）：大纲要求的章节是否齐全

### Gate 决策

- pass → 渲染
- retry → 重写不合格章节（LangGraph 条件边）
- degrade → 替换不可验证数据后渲染
- block → 拒绝发布

可选引入 Guardrails AI 做校验编排，现有 checker 作为自定义 validator 注册。

---

## 11. 渲染（前端只管 JSON → 视觉）

- Jinja2 模板直接消费 `Brief.model_dump()`，不再解析 Markdown
- `markdown_parser.py` (370 行) **删除**
- 模板内用 `{% for section in sections %}` 遍历结构化数据
- Tailwind CSS + DaisyUI（CDN）
- Playwright `page.pdf()` 导出 PDF

---

## 12. 能力扩展：任意题材

### Planner Agent

用户说一句话 → AI 理解领域 → 选源 → 定结构 → 生成。

输出 `TaskConfig`：topic、period、focus_areas、selected_sources、
source_config、report_structure（list[SectionPlan]）、tone、target_audience。

### UserProfile（偏好存储）

记录用户的 default_focus、preferred_sources、source_overrides、
excluded_topics、tone_preference，下次不用重复说。

### 典型场景

- "做个每日AI新闻" → 选 [hackernews, 36kr, hf_papers, github_trending]
- "今天A股怎么样" → 选 [akshare_stock, wallstreetcn, cn_economy]
- "OCR技术周报，要GitHub竞品" → 选 [github_trending, arxiv, hf_papers] + 竞品配置

---

## 13. 目录结构

```
clawcat/
  PLAN.md
  SKILL.md
  config.yaml
  .env
  requirements.txt

  schema/
    brief.py             # Brief / BriefSection / BriefItem / ClawComment
    task.py              # TaskConfig / SectionPlan / SourceSelection
    item.py              # Item / FetchResult
    user.py              # UserProfile

  adapters/
    registry.json        # 源目录（AI 读这个来选源）
    base.py              # 统一接口
    news/                # 36kr, wallstreetcn, weibo, tencent, v2ex, cn_economy, rss
    finance/             # akshare_stock, akshare_macro
    tech/                # github_trending, hf_papers, arxiv, hackernews

  graph.py               # LangGraph StateGraph 定义（~100 行）

  nodes/
    planner.py           # Planner Agent
    fetch.py             # 动态加载 adapter + 时间过滤
    dedup.py             # LangMem 去重
    select.py            # LLM 选材
    summarize.py         # Map 摘要
    plan.py              # 大纲生成
    write_section.py     # 按节生成 BriefSection
    check_section.py     # 章节级 grounding
    revise_section.py    # 重写不合格章节
    assemble.py          # 拼接全文
    final_check.py       # 全文一致性 + 覆盖率
    degrade.py           # 降级替换
    render.py            # Jinja2 + Playwright
    save.py              # LangMem 保存条目记忆

  grounding/
    protocol.py          # GroundingChecker 接口
    temporal.py
    entity.py
    numeric.py
    structure.py
    consistency.py       # 新增：跨节一致性
    coverage.py          # 新增：覆盖率

  prompts/               # 各场景 prompt 模板
  templates/             # Jinja2 HTML 模板
  static/                # logo 等静态资源
```

---

## 14. 依赖

```
langchain-openai
langgraph
instructor
pydantic>=2.0
pydantic-settings
langmem
feedparser
playwright
httpx
jinja2
pyyaml
akshare
pandas
```

---

## 15. 实施路线

### Phase 1：基础骨架（最先做）

1. 用 Pydantic v2 定义所有 schema（Brief, TaskConfig, Item, UserProfile）
2. 用 pydantic-settings 替代手写配置
3. 用 LangGraph 搭建最小 pipeline（fetch → write → render）
4. 用 instructor + ChatOpenAI 实现单节生成

### Phase 2：数据层

5. Copy ClawHub skill 代码到 adapters/，建立 registry.json
6. 实现时间过滤五层保障
7. 用 feedparser 替代手写 RSS 解析

### Phase 3：质量控制

8. 实现 Map-Plan-Write 多步生成
9. 接入 grounding checkers（章节级 + 全文级）
10. 用 LangGraph 条件边实现 gate 决策（pass/retry/degrade/block）

### Phase 4：智能化

11. 实现 Planner Agent（任意题材 → 自动选源定结构）
12. 接入 LangMem 去重
13. 实现 LLM 选材
14. 实现 UserProfile 偏好存储

### Phase 5：交付与打磨

15. Jinja2 模板改为消费 Brief JSON
16. Playwright 替代 WeasyPrint
17. 重写 README 和 SKILL.md
18. 精读 Open Deep Research + 完成 LangChain Academy 课程

---

## 16. 简历叙事

> 基于 LangGraph 构建 AI 驱动的任意题材简报引擎：Planner Agent 自动理解用户需求、
> 从数据源目录动态选择信息来源，通过 Map-Plan-Write 多步生成 pipeline 产出结构化
> Brief（Pydantic schema），4 维 grounding 检测 + 4 态质量门禁实现章节级自动重试
> 与降级，前端通过 schema 合约完全解耦，Jinja2 + Playwright 渲染 HTML/PDF。
> 架构借鉴 Open Deep Research，支持 LangMem 跨期去重与用户偏好记忆。

覆盖面试考点：Agent 设计、结构化输出、Prompt 工程、质量控制、多步编排、
架构解耦、框架选型、工程实践。
