# 🦞 clawCat-brief

通用简报引擎 — 一句话输入，自动选源、多步生成、结构化校验，输出 HTML / PDF / PNG / Markdown 报告。

提供两种运行模式：**独立模式**（自带 LLM pipeline）和 **Skill 模式**（作为 Cursor/OpenClaw 等宿主 AI 的工具插件，零 LLM 依赖）。

## 核心特性

- **Planner Agent** — 一句话输入 → 自动从 `registry.json` 选择数据源 → 设计报告结构
- **意图全链路贯穿** — `focus_areas` / `tone` / `target_audience` 注入 Select → Summarize → Plan → Write → Revise → Assemble 全部节点
- **Map-Plan-Write 多步生成** — 并行摘要 → 大纲 → 按节并行生成，每步认知负荷低，失败只重做该步
- **LangGraph Send 并行** — summarize 和 write 阶段使用 LangGraph 原生 fan-out/fan-in
- **4 维 Grounding 校验** — 时间 / 实体 / 数值 / 结构，章节级自动重试
- **4 态质量门禁** — PASS / RETRY / DEGRADE / BLOCK，条件边驱动
- **结构化输出** — instructor（Mode.MD_JSON）直接输出 Pydantic 对象，兼容第三方模型
- **Schema 合约解耦** — 渲染层只消费 `Brief.model_dump()` JSON，与生成层零耦合
- **Skill 模式** — `clawcat_skill/` 提供 `plan_report` / `fetch_data` / `render_report` 三个工具函数，宿主 AI 负责内容生成，本项目只做 I/O
- **Skill Proxy 适配器** — 通过 `skill_proxy` 桥接外部搜索 Skill（如 miaoda_unified），统一纳入 `registry.json` 管理
- **16 个数据源** — 搜索引擎、科技新闻、中国财经、开源项目、学术论文、社交热点、外部 Skill 代理
- **4 种输出格式** — HTML / PDF（A4）/ PNG（手机长截屏 @2x）/ Markdown

## 架构

```
用户输入 → Planner → Fetch(并行) → Dedup → Select
           → [Send fan-out] Summarize(并行) → Plan
           → [Send fan-out] Write(并行) → Gather → Check → Assemble → FinalCheck → Render → Save
                                                                          ↑            |
                                                                          └── revise ──┘
```

基于 **LangGraph StateGraph** 编排，每个节点独立、可重试、可并行。

## 设计决策与问题解决

### 问题 1：上下文爆炸

**问题**：早期版本用单次 LLM 调用生成整篇报告，100+ 条素材 + 完整报告结构塞进一个 prompt，导致 LLM 输出质量下降、遗漏信息、幻觉增多。

**解决方案**：采用 **Map-Plan-Write** 多步架构，每步只处理一小块：
1. **Map（摘要）** — 将素材分成 5 条一批并行摘要，每个 LLM 调用只处理 5 条
2. **Plan（大纲）** — 基于摘要设计报告大纲，不需要看原始素材全文
3. **Write（撰写）** — 每个章节独立生成，互不干扰
4. **Check（校验）** — 独立检查每个章节的事实准确性

使用 **LangGraph Send** 原生 fan-out 实现真正并行，而不是手动 `asyncio.gather`。这避免了绕过框架自己造轮子，同时获得了 LangGraph 内置的状态管理和错误处理。

### 问题 2：GitHub 总是推荐那几个老项目

**问题**：GitHub Search API 默认按 stars 排序，每次搜索 "OCR" 都返回 PaddleOCR、EasyOCR 等老面孔，新项目被埋没。

**解决方案**：实现**三策略搜索**，由 Planner Agent 动态配置：
- **rising** — `created:>{90天前} pushed:>{本周}` 按 stars 排序 → 近期创建且快速增长的项目
- **created** — `created:>{本周}` 按 stars 排序 → 全新发布的项目
- **updated** — `pushed:>{本周}` 按更新时间排序 → 活跃维护的项目

同时 Planner 会在搜索词中加入竞品对比词（如 "OCR alternative"、"OCR vs"），自动生成竞品分析章节。

### 问题 3：行业新闻覆盖不足

**问题**：早期只依赖 RSS 和特定 API（如 36kr、HackerNews），但 36kr API 不稳定（持续 500 错误），HackerNews 对中文主题几乎无结果，导致"阿里开源 OCR 模型"这样的大新闻完全缺失。

**解决方案**：
1. **新增搜索引擎数据源** — DuckDuckGo（免 Key、全球新闻、自带日期字段）+ 百度搜索（免 Key、国内直达），Planner 自动为搜索词配置中英文关键词和大厂名称
2. **36kr 三路降级** — 热门 API → 搜索 API → RSS 回退，任何一路可用就能拿到数据
3. **Planner 引导策略** — prompt 中明确要求技术类报告必选 36kr + 搜索引擎，配置中文关键词

现在 6-7 个数据源并行抓取，每次可获得 100+ 条素材，大厂动态基本不会遗漏。

### 问题 4：LLM 输出格式不可控

**问题**：让 LLM 输出 Markdown 再 parse，格式五花八门，经常 parse 失败，且无法保证必填字段完整。

**解决方案**：全面使用 **instructor** 库，LLM 调用直接返回 Pydantic 对象：
```python
result = client.chat.completions.create(
    model=get_model(),
    response_model=BriefSection,  # 直接指定 Pydantic schema
    messages=[...],
    max_retries=get_max_retries(),  # instructor 自动重试
)
```
所有 LLM 节点（Planner、Select、Summarize、Plan、Write、Revise、Assemble）统一走这条路径。

### 问题 5：报告质量无保障

**问题**：LLM 容易编造日期、数字、实体名，也会遗漏大纲要求的章节。

**解决方案**：**两级质量检查 + 自动重试**：
- **章节级**（hard check）：TemporalGrounder（日期范围）、NumericGrounder（数值溯源）
- **章节级**（soft check）：EntityGrounder（实体名匹配，仅 warn 不阻断）
- **全文级**：ConsistencyChecker（跨节矛盾）、CoverageChecker（章节完整性）、StructureGrounder（结构合规）

EntityGrounder 故意设为 soft check，因为 LLM 对实体名的表述与原始素材天然不完全匹配，强制重试只会浪费时间且无法真正改善。

### 问题 6：并行与事件循环冲突

**问题**：LangGraph 节点内嵌套 `asyncio.run()` 调用异步适配器，当 LangGraph 本身运行在事件循环中时会引发冲突。

**解决方案**：fetch 节点检测当前是否已有事件循环运行，如有则通过 `ThreadPoolExecutor` 分发异步任务到独立线程，避免嵌套事件循环。summarize 和 write 节点使用 LangGraph Send 原生并行，彻底避免手动事件循环管理。

### 问题 7：Claw 锐评结构混乱

**问题**：早期每个章节的每个条目都带完整 claw_comment，导致大量重复且低质量的评论。

**解决方案**：采用**混合模式**：
- 一般章节的条目只带 `verdict` 一句话短评（10-20 字）
- 末尾专门的「Claw 锐评」章节才使用完整的 `claw_comment`（highlight + concerns + verdict）

通过 prompt 指令 + 模板分支实现，`section_type == "review"` 时渲染完整锐评，其他章节只渲染 verdict。

### 问题 8：结构化意图在管道中流失

**问题**：Planner Agent 花一次 LLM 调用，将"美股周报"理解为 `focus_areas=["美国股市", "美联储政策", "科技股财报"]`、`tone="analytical"`、`target_audience="投资者"`。但下游 Select、Summarize、Write、Revise、Assemble 节点只读 `topic` 字符串，让自己的 LLM 重新猜测已知信息——猜错了（"美股周报"中出现 A 股医药、小米汽车）。

这暴露了一个多 Agent 管道中的典型反模式：**上游 LLM 生产的结构化信息，在传递给下游时退化成了字符串**。

**解决方案**：将 `TaskConfig` 中的 `focus_areas`、`tone`、`target_audience` 贯穿注入整条生成链路——Summarize（按维度提取角度）、Plan（按维度组织大纲）、Write（按风格和受众写作）、Revise（修订时保持一致风格）、Assemble（执行摘要保持风格）。不做任何硬编码规则，所有约束都来自 Planner 的结构化输出。

### 问题 9：instructor Mode 与第三方模型不兼容

**问题**：`instructor.Mode.JSON` 依赖模型在 system prompt 层面理解"只输出 JSON"——这是一个**提示层约束**，取决于模型自身对 JSON Mode 的实现。kimi-k2.5 等非 OpenAI 原生模型的 JSON Mode 实现不完整，输出混入 XML 标签。

**解决方案**：先切换到 `instructor.Mode.TOOLS`（Function Calling 协议），发现 thinking 模型（如 qwen3.5-plus）不支持 `tool_choice: required` 参数。最终采用 `instructor.Mode.MD_JSON`——让 LLM 在 markdown 代码块中输出 JSON，instructor 自动提取并校验。这是三种 Mode 中兼容性最好的方案，不依赖 JSON Mode 实现、不依赖 tool_choice 支持。

**教训**："API 兼容"不等于"行为一致"。`Mode.JSON`（提示层约束）→ `Mode.TOOLS`（协议层约束）→ `Mode.MD_JSON`（格式提取层约束），每一步都是在减少对模型特定行为的隐性依赖。

### 问题 10：Skill 内置 LLM 与宿主环境的冲突

**问题**：项目作为 Cursor/OpenClaw 的 Skill 使用时，pipeline 内部自带 LLM 调用（planner、select、summarize、write、check 共 10+ 次），宿主 AI 无法介入内容生成过程。这导致两个实际问题：(1) 用户需要额外配置 API Key，即使宿主环境已经有 LLM 能力；(2) 宿主 AI 的上下文知识（如用户偏好、对话历史）无法传递给 pipeline 内部的 LLM 调用。

**解决方案**：将项目拆分为两个独立包：

- `clawcat/` — 完整 pipeline，自带 LLM，通过 CLI 独立运行
- `clawcat_skill/` — 只暴露三个纯 I/O 工具函数，不调 LLM

`clawcat_skill` 的三个函数分工：
1. `plan_report(query)` — 规则匹配推断主题/周期，返回可用数据源列表（读 `registry.json`，不调 LLM）
2. `fetch_data(task_config)` — 并行抓取 + 去重 + 时间过滤（复用 `clawcat.nodes.fetch` 和 `dedup`，不调 LLM）
3. `render_report(brief)` — Jinja2 HTML + Playwright PDF/PNG（复用 `clawcat.nodes.render`，不调 LLM）

宿主 AI 读 `SKILL.md` 获取 Brief Schema 和写作指令，自己完成"选材→撰写→质检"这三步，调工具完成"抓数据→渲染"。这样宿主的上下文、对话历史、用户偏好都能自然地融入内容生成，不存在信息断层。

### 问题 11：外部数据 Skill 无法复用

**问题**：ClawHub 上有大量搜索类 Skill（如 miaoda_unified），但它们的接口各不相同，无法直接接入 `fetch_data` 的数据管道。如果让宿主 AI 自己分别调用多个 Skill 再合并结果，编排逻辑重复且容易出错。

**解决方案**：新建 `skill_proxy` 适配器（`clawcat/adapters/search/skill_proxy.py`），统一桥接外部 Skill：

- 在 `registry.json` 中声明为普通数据源，和内置的 duckduckgo、baidu 平级
- 通过 `skill_module` 指定目标 Skill 的 Python 模块路径，`skill_function` 指定函数名
- 自动将 Skill 返回的 `{title, url, snippet, date}` 转换为统一的 `Item` 格式
- 支持任何遵循 `search(query, max_results) -> list[dict]` 接口的 Skill

这样新增外部数据源只需在 `registry.json` 加一条配置，不用改代码。

### 问题 12：报告字数多但观点弱

**问题**：模型默认行为是面面俱到、两面讨好。生成的周报信息量大，但读完不知道"所以呢"——缺乏明确立场。

**解决方案**：从三个层面控制：

1. **Persona 行为描述** — 不是"你是分析师"，而是"你为高级决策者撰写简报，他们只关心这件事对我意味着什么"。行为描述比角色名称更能约束输出风格
2. **禁止清单** — 明确禁止"值得关注""不容忽视""一方面另一方面"等空洞表述。"不要做什么"比"要做什么"更能改变默认行为
3. **字数纪律从结构拆分** — 每条目 summary 控制在 80-200 字，prose 控制在 100-300 字。在输入端截断素材比在输出端限制 token 更有效

## 技术栈

| 组件 | 用途 |
|------|------|
| **LangGraph** | Pipeline 编排（StateGraph + Send 并行 + 条件边 + retry loop） |
| **instructor** | 结构化 LLM 输出（Pydantic 校验 + 自动重试） |
| **Pydantic v2** | Schema 定义 + 数据校验 |
| **pydantic-settings** | 配置管理（YAML + .env + 环境变量） |
| **ddgs** | DuckDuckGo 搜索引擎（免 Key，新闻搜索自带日期） |
| **baidusearch** | 百度搜索引擎（免 Key，国内直达） |
| **feedparser** | RSS/Atom 解析 |
| **httpx** | 异步 HTTP 客户端 |
| **Jinja2 + DaisyUI** | HTML 渲染 |
| **Playwright** | HTML → PDF / PNG 导出（使用系统 Chrome） |
| **AKShare** | A 股 / 宏观经济数据 |

## 样例报告

<div align="center">
<img src="docs/sample_report.png" width="390" alt="OCR 技术周报样例（手机长截屏）" />
<p><em>OCR 技术周报 — 手机长截屏 PNG 输出（@2x Retina）</em></p>
</div>

## 快速开始

### 模式一：独立运行（自带 LLM）

```bash
pip install -r requirements.txt

cp config.yaml config.local.yaml
# 编辑 config.local.yaml，设置 llm.api_key
# 或: export LLM__API_KEY=sk-xxx

python -m clawcat.cli "做个每日AI新闻"
python -m clawcat.cli "OCR技术周报，重点关注大厂开源动态和竞品分析"
```

### 模式二：Skill 模式（宿主 AI 调用）

不需要配置 LLM API Key。宿主 AI 读取 `clawcat_skill/SKILL.md` 后，调用三个工具函数：

```python
from clawcat_skill import plan_report, fetch_data, render_report

# 1. 规划：解析意图，返回可用数据源
plan = plan_report("OCR 技术周报")

# 2. 抓取：并行获取 + 去重
data = fetch_data({
    "topic": "OCR技术",
    "period": "weekly",
    "selected_sources": [
        {"source_name": "hackernews", "config": {"queries": ["OCR"]}},
        {"source_name": "36kr", "config": {"queries": ["OCR", "文字识别"]}},
    ],
    "since": "2026-03-09T00:00:00",
    "until": "2026-03-16T12:00:00",
})

# 3. 宿主 AI 基于 data["items"] 撰写 Brief（schema 定义见 SKILL.md）

# 4. 渲染：Brief dict → HTML/PDF/PNG
output = render_report(brief_dict, output_dir="output")
```

外部搜索 Skill 可通过 `skill_proxy` 适配器接入：

```python
{"source_name": "skill_proxy", "config": {
    "skill_module": "miaoda_unified.search",
    "queries": ["AI 大模型"],
    "source_label": "miaoda"
}}
```

## 目录结构

```
clawcat/                 # 独立模式：完整 LangGraph pipeline
  adapters/              # 数据源适配器 + registry.json
    news/                # 36kr, wallstreetcn, weibo, tencent, v2ex, cn_economy, rss
    finance/             # akshare_stock, akshare_macro
    tech/                # github_trending, hackernews, arxiv, hf_papers
    search/              # duckduckgo, baidu, skill_proxy
  nodes/                 # LangGraph 节点（15 个）
  grounding/             # 质量检查器（6 个）
  prompts/               # 提示词模板
  schema/                # Pydantic 模型（Brief, TaskConfig, Item, UserProfile）
  templates/             # Jinja2 HTML 模板
  graph.py               # StateGraph 定义
  state.py               # Pipeline 状态
  config.py              # pydantic-settings 配置
  llm.py                 # instructor 客户端工厂
  cli.py                 # CLI 入口

clawcat_skill/           # Skill 模式：宿主 AI 调用的工具包
  __init__.py            # 导出 plan_report, fetch_data, render_report
  tools.py               # 三个工具函数（纯 I/O，零 LLM）
  SKILL.md               # 宿主 AI 使用手册（API + Schema + 写作指令）

testcode/                # 测试代码
```

## 数据源

所有数据源代码 copy 到本地统一管理，通过 `registry.json` 声明能力，Planner Agent 动态选取。

| 源 | 类型 | 覆盖 | 中国可访问 | 需 API Key |
|----|------|------|-----------|-----------|
| duckduckgo | 搜索引擎 | 全球 | ✅ | 否 |
| baidu | 搜索引擎 | 中国 | ✅ | 否 |
| github_trending | 开源项目 | 全球 | ✅ | 否（有 Token 更好） |
| hackernews | 科技新闻 | 全球 | ✅ | 否 |
| hf_papers | AI 论文 | 全球 | ✅ | 否 |
| arxiv | 学术论文 | 全球 | ✅ | 否 |
| 36kr | 科技/创投 | 中国 | ✅ | 否 |
| wallstreetcn | 金融/宏观 | 中国 | ✅ | 否 |
| weibo | 社交热点 | 中国 | ✅ | 否 |
| tencent | 综合新闻 | 中国 | ✅ | 否 |
| v2ex | 开发者社区 | 中国 | ✅ | 否 |
| cn_economy | 经济资讯 | 中国 | ✅ | 否 |
| akshare_stock | 股市行情 | 中国 | ✅ | 否 |
| akshare_macro | 宏观数据 | 中国 | ✅ | 否 |
| rss | 通用 RSS | 全球 | 视源而定 | 否 |
| skill_proxy | 外部 Skill 代理 | 视 Skill | ✅ | 否 |

## License

MIT

---

*Built by llx & Luna 🐱 — where the claw meets the code.* 🦞
