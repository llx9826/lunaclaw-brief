# ClawCat Skill — 宿主 AI 简报生成工具

你拥有三个工具函数，可以帮用户生成结构化简报（日报/周报/行业分析）。
你是内容撰写者和质量把关者——工具只负责数据获取和渲染，你负责分析素材并撰写报告。

## 快速流程

```
Step 1: plan  → 调用 plan_report(query) 获取数据源建议
Step 2: fetch → 调用 fetch_data(task_config) 抓取并去重素材
Step 3: 你撰写 Brief（按下方 Schema）
Step 4: render → 调用 render_report(brief) 渲染为 HTML/PDF/PNG
```

---

## 工具 API

### 1. `plan_report(query: str) -> dict`

解析用户意图，返回建议配置和可用数据源。不调用 LLM。

```python
from clawcat_skill import plan_report

result = plan_report("OCR 技术周报")
```

**返回值:**
```json
{
  "suggested_config": {
    "topic": "OCR 技术周报",
    "period": "weekly",
    "inferred_domains": ["tech", "ai", "cv"],
    "since": "2026-03-09T00:00:00",
    "until": "2026-03-16T12:00:00"
  },
  "matched_sources": [
    {
      "name": "hackernews",
      "module": "clawcat.adapters.tech.hackernews",
      "domains": ["tech", "startup", "ai"],
      "description": "Hacker News stories via Algolia search API",
      "config_params": { "queries": "list[str]", "min_points": "int" },
      "config_guidance": "Set queries to topic-relevant English keywords"
    }
  ],
  "all_sources": [ ... ],
  "user_profile": { ... }
}
```

**你需要做的：** 审查 `matched_sources`，从中选择合适的数据源，为每个源配置 `config`（特别是 `queries` 关键词），组装成 `task_config` 传给 `fetch_data`。

### 2. `fetch_data(task_config: dict) -> dict`

根据配置并行抓取多个数据源，自动去重和时间过滤。不调用 LLM。

```python
from clawcat_skill import fetch_data

result = fetch_data({
    "topic": "OCR技术",
    "period": "weekly",
    "selected_sources": [
        {"source_name": "hackernews", "config": {"queries": ["OCR", "text recognition"]}},
        {"source_name": "github_trending", "config": {"queries": ["OCR", "OCR alternative"]}},
        {"source_name": "36kr", "config": {"queries": ["OCR", "文字识别"]}},
        {"source_name": "arxiv", "config": {}},
        {"source_name": "duckduckgo", "config": {"queries": ["OCR open source 2026", "OCR 开源"]}}
    ],
    "since": "2026-03-09T00:00:00",
    "until": "2026-03-16T12:00:00",
    "max_items": 30
})
```

**返回值:**
```json
{
  "items": [
    {
      "title": "PaddleOCR v3 Released",
      "url": "https://...",
      "source": "github_trending",
      "raw_text": "...",
      "published_at": "2026-03-14T10:00:00",
      "item_id": "a1b2c3d4",
      "meta": {}
    }
  ],
  "stats": {
    "total_fetched": 85,
    "after_dedup": 42,
    "sources_used": ["hackernews", "github_trending", "36kr"]
  }
}
```

**你需要做的：** 阅读 `items`，筛选出最有价值的素材，然后撰写 Brief。

### 3. `render_report(brief: dict, output_dir: str = "output") -> dict`

将你生成的 Brief 对象渲染为 HTML/PDF/PNG/Markdown/JSON。不调用 LLM。

```python
from clawcat_skill import render_report

result = render_report(brief_dict, output_dir="output")
```

**返回值:**
```json
{
  "html_path": "output/weekly_2026-03-16_20260316_120000.html",
  "pdf_path": "output/weekly_2026-03-16_20260316_120000.pdf",
  "png_path": "output/weekly_2026-03-16_20260316_120000.png",
  "json_path": "output/weekly_2026-03-16_20260316_120000.json",
  "md_path": "output/weekly_2026-03-16_20260316_120000.md"
}
```

---

## Brief Schema（你生成的输出结构）

你必须按以下结构生成 `brief` dict，传给 `render_report`。

### 顶层: Brief

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `schema_version` | str | 否 | 固定 `"1.0"` |
| `report_type` | str | 是 | `"daily"` 或 `"weekly"` |
| `title` | str | 是 | 报告标题，如 `"OCR 技术 · 每周概览"` |
| `issue_label` | str | 是 | 期号，用日期格式如 `"2026-03-16"` |
| `time_range` | TimeRange | 是 | 见下方 |
| `executive_summary` | str | 是 | 2-3 句话概括核心要点 |
| `sections` | list[BriefSection] | 是 | 报告章节列表 |
| `metadata` | BriefMetadata | 否 | 元数据 |

### TimeRange

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_requested` | str | 用户原始请求 |
| `resolved_start` | str | 实际覆盖起始时间 (ISO) |
| `resolved_end` | str | 实际覆盖结束时间 (ISO) |
| `report_generated` | str | 报告生成时间 (ISO) |
| `coverage_gaps` | list[str] | 数据覆盖空白说明 |

### BriefSection

| 字段 | 类型 | 说明 |
|------|------|------|
| `heading` | str | 章节标题 |
| `section_type` | str | `"hero"` / `"items"` / `"analysis"` / `"review"` |
| `icon` | str | 章节图标 emoji |
| `prose` | str | 章节导语/综合分析（1-2 段散文） |
| `items` | list[BriefItem] | 该章节的条目列表 |

### BriefItem

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | str | 条目标题 |
| `summary` | str | 80-200 字摘要，结论先行 |
| `key_facts` | list[str] | 关键数据点 |
| `verdict` | str \| null | 一句话短评（非 review 章节用） |
| `claw_comment` | ClawComment \| null | Claw 锐评（仅 review 章节用） |
| `sources` | list[str] | 数据来源 URL |
| `tags` | list[str] | 标签 |

### ClawComment（仅用于 `section_type = "review"` 的章节）

| 字段 | 类型 | 说明 |
|------|------|------|
| `highlight` | str | 一句话犀利点评（金句） |
| `concerns` | list[str] | 1-3 个风险/疑虑 |
| `verdict` | str | 总结判断（看好/看空/观望 + 理由） |

### BriefMetadata

| 字段 | 类型 | 说明 |
|------|------|------|
| `sources_used` | list[str] | 使用的数据源名称 |
| `items_fetched` | int | 抓取条目数 |
| `items_selected` | int | 选用条目数 |

---

## 写作指令

撰写 Brief 内容时，严格遵循以下规则：

### 铁律

1. **数据锚定** — 所有数值必须引用自 `items` 素材。素材未提供的数据写「数据未披露」，绝不编造
2. **结论先行** — 每个 `summary` 的第一句必须是明确判断，不能是背景描述
3. **信息密度** — 每 100 字至少包含 1 个具体数据、事实或案例
4. **深度优先** — 宁可深入 2 个点，也不要浅谈 5 个点
5. **字数纪律** — 每个 `summary` 控制在 80-200 字；`prose` 控制在 100-300 字

### 禁止

- 禁止编造素材中不存在的数值（最严重的错误）
- 禁止「值得关注」「不容忽视」「引发热议」等空洞表述
- 禁止「一方面…另一方面…」的骑墙式平衡
- 禁止段落末尾的总结性废话
- 禁止以「随着…的发展」开头
- 禁止重复前序章节已经提到的内容

### 章节类型指引

| section_type | 说明 | verdict/claw_comment |
|-------------|------|---------------------|
| `hero` | 焦点头条，1-3 条最重要事件 | 用 `verdict` |
| `items` | 行业动态/新闻列表 | 用 `verdict` |
| `analysis` | 深度分析/竞品对比 | 用 `verdict` |
| `review` | Claw 锐评章节 | 用 `claw_comment`（必填） |

### Claw 锐评风格

- `highlight`: 读者看完会记住的金句，锐利有态度
- `concerns`: 具体风险，不要空洞
- `verdict`: 明确方向（看好/看空/观望），附理由
- 语气犀利有态度，但有理有据。禁止「值得持续关注」等和稀泥表述

### 报告结构建议

**日报**（3 个章节）:
1. `hero` — 焦点头条（1-2 条）
2. `items` — 行业动态（3-5 条）
3. `review` — Claw 锐评（2-3 条）

**周报**（4-5 个章节）:
1. `hero` — 本周焦点（2-3 条）
2. `items` — 行业动态（3-5 条）
3. `analysis` — 深度分析/竞品对比（2-3 条）
4. `items` — 社区/学术进展（2-3 条）
5. `review` — Claw 锐评（2-3 条）

---

## 质量检查清单

在调用 `render_report` 之前，逐项自查：

- [ ] 所有数值都来自 `items` 素材，无编造
- [ ] 每个 `summary` 第一句是判断，不是背景
- [ ] 无「值得关注」等空洞表述
- [ ] `review` 章节的每个条目都有 `claw_comment`
- [ ] 非 `review` 章节用 `verdict` 而非 `claw_comment`
- [ ] 日报总字数 < 2000 字，周报总字数 < 4000 字
- [ ] `issue_label` 使用日期格式（如 `2026-03-16`）
- [ ] `executive_summary` 不超过 3 句话
- [ ] 无重复内容跨章节出现

---

## 完整示例

用户说：**"帮我做个 OCR 技术周报"**

### Step 1: 规划

```python
from clawcat_skill import plan_report
plan = plan_report("帮我做个 OCR 技术周报")
# 查看 plan["matched_sources"]，选择合适的数据源
```

### Step 2: 抓取数据

```python
from clawcat_skill import fetch_data
data = fetch_data({
    "topic": "OCR技术",
    "period": "weekly",
    "selected_sources": [
        {"source_name": "hackernews", "config": {"queries": ["OCR", "text recognition", "document AI"]}},
        {"source_name": "github_trending", "config": {"queries": ["OCR", "OCR alternative", "document AI"]}},
        {"source_name": "36kr", "config": {"queries": ["OCR", "文字识别", "文档智能"]}},
        {"source_name": "arxiv", "config": {}},
        {"source_name": "duckduckgo", "config": {"queries": ["OCR 开源", "text recognition 2026"]}}
    ],
    "since": "2026-03-09T00:00:00",
    "until": "2026-03-16T12:00:00",
    "max_items": 30
})
# data["items"] 包含去重后的素材列表
```

### Step 3: 撰写 Brief

分析 `data["items"]`，按 Brief Schema 撰写报告：

```python
brief = {
    "schema_version": "1.0",
    "report_type": "weekly",
    "title": "OCR 技术 · 每周概览",
    "issue_label": "2026-03-16",
    "time_range": {
        "user_requested": "帮我做个 OCR 技术周报",
        "resolved_start": "2026-03-09T00:00:00",
        "resolved_end": "2026-03-16T12:00:00",
        "report_generated": "2026-03-16T12:00:00"
    },
    "executive_summary": "本周 OCR 领域最大事件是 PaddleOCR v3 发布...",
    "sections": [
        {
            "heading": "焦点头条",
            "section_type": "hero",
            "icon": "🔥",
            "prose": "本周 OCR 领域迎来重要更新...",
            "items": [
                {
                    "title": "PaddleOCR v3 正式开源",
                    "summary": "百度发布 PaddleOCR v3，端到端识别准确率提升 12%...",
                    "key_facts": ["准确率提升 12%", "支持 80+ 语种"],
                    "verdict": "中文 OCR 开源生态的里程碑式更新",
                    "sources": ["https://github.com/PaddlePaddle/PaddleOCR"],
                    "tags": ["开源", "OCR"]
                }
            ]
        },
        {
            "heading": "Claw 锐评",
            "section_type": "review",
            "icon": "🦞",
            "prose": "",
            "items": [
                {
                    "title": "PaddleOCR v3 的战略意义",
                    "summary": "PaddleOCR v3 不只是技术升级...",
                    "key_facts": [],
                    "claw_comment": {
                        "highlight": "百度用开源打响了中文 OCR 的价格战",
                        "concerns": ["商业化路径不清晰", "社区贡献者增长缓慢"],
                        "verdict": "短期看好开源生态扩张，但商业闭环仍需验证"
                    },
                    "sources": [],
                    "tags": []
                }
            ]
        }
    ],
    "metadata": {
        "sources_used": ["hackernews", "github_trending", "36kr"],
        "items_fetched": 85,
        "items_selected": 12
    }
}
```

### Step 4: 渲染

```python
from clawcat_skill import render_report
output = render_report(brief, output_dir="output")
# output["html_path"] → 可直接浏览器打开
# output["pdf_path"] → 可打印的 PDF
# output["png_path"] → 移动端长截图
```

---

## 数据源配置指南

常用数据源及配置建议：

| 数据源 | 适用场景 | config 要点 |
|--------|---------|-------------|
| `hackernews` | 全球科技新闻 | `queries`: 英文关键词 |
| `github_trending` | 开源项目发现 | `queries`: 包含核心词+竞品词 |
| `36kr` | 中国科技行业 | `queries`: 中文关键词 |
| `arxiv` | 学术论文 | 无需特别配置 |
| `hf_papers` | AI/ML 论文 | 无需特别配置 |
| `duckduckgo` | 通用新闻搜索 | `queries`: 中英文都写; `use_news`: true |
| `baidu` | 中文新闻搜索 | `queries`: 中文关键词 |
| `wallstreetcn` | 金融新闻 | 无需特别配置 |
| `akshare_stock` | A股/港股数据 | 无需特别配置 |
| `akshare_macro` | 宏观经济指标 | 无需特别配置 |
| `cn_economy` | 中国经济新闻 | 无需特别配置 |
| `weibo` | 微博热搜 | 无需特别配置 |
| `tencent` | 腾讯新闻 | 无需特别配置 |
| `v2ex` | 开发者社区 | 无需特别配置 |
| `rss` | 自定义 RSS | 需要传 `feeds` URL 列表 |
| `skill_proxy` | 桥接外部搜索 Skill | `skill_module` + `queries`，见下方 |

### 使用外部 Skill 作为数据源（skill_proxy）

如果本地安装了其他搜索类 skill（如 `miaoda_unified`），可以通过 `skill_proxy` 适配器将它们作为数据源接入：

```python
{"source_name": "skill_proxy", "config": {
    "skill_module": "miaoda_unified.search",
    "skill_function": "search",
    "queries": ["AI 大模型", "LLM 开源"],
    "max_results": 10,
    "source_label": "miaoda"
}}
```

`skill_proxy` 会自动调用指定 skill 模块的搜索函数，将返回结果转换为统一的 `Item` 格式，和其他内置数据源一起参与去重和过滤。

支持任何遵循以下接口的 skill：
- 函数签名: `search(query: str, max_results: int, **kwargs) -> list[dict]`
- 返回 dict 包含: `title`, `url`（必填），`snippet`/`summary`, `date`（可选）

---

*ClawCat Skill v1.0 · Built by llx & Luna 🐱🦞*
