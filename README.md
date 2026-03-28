# 🦞 clawCat-BRIEF

AI 驱动的通用简报引擎 — 用户说一句话，自动理解需求、选择数据源、多步生成、结构化校验，输出 HTML/PDF 简报。

## 核心特性

- **Planner Agent** — 用户一句话输入，AI 自动理解领域、从 `registry.json` 选择数据源、设计报告结构
- **Map-Plan-Write 多步生成** — 并行摘要 → 大纲 → 按节并行生成，每步认知负荷低，失败只重做该步
- **LangGraph Send 并行** — summarize 和 write 阶段使用 LangGraph 原生 fan-out/fan-in，真正并行
- **4 维 Grounding 校验** — 时间 / 实体 / 数值 / 结构，章节级自动重试
- **4 态质量门禁** — PASS / RETRY / DEGRADE / BLOCK，LangGraph 条件边驱动
- **结构化输出** — LLM 通过 instructor 直接输出 Pydantic 对象，不再 parse 自由文本
- **Schema 合约解耦** — 渲染层只消费 `Brief.model_dump()` JSON，与生成层零耦合
- **15 个数据源** — 覆盖搜索引擎、科技新闻、中国财经、开源项目、学术论文、社交热点
- **搜索引擎集成** — DuckDuckGo + 百度搜索，确保大厂新闻和行业动态不遗漏
- **GitHub 三策略搜索** — rising（新且快速增长）+ created（全新项目）+ updated（活跃项目）
- **跨期去重** — 基于 item_id 精确去重，避免周报/日报反复报道同一项目
- **5 层新鲜度保障** — 周报只讲这周、日报只讲今天，全链路硬约束
- **Claw 锐评** — 每篇报告附带犀利、有态度的 AI 点评

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
| **Playwright** | HTML → PDF 导出 |
| **AKShare** | A 股 / 宏观经济数据 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium  # 可选，PDF 导出需要

# 2. 配置 API Key
cp config.yaml config.local.yaml
# 编辑 config.local.yaml，设置 llm.api_key
# 或设置环境变量：export LLM__API_KEY=sk-xxx

# 3. 运行
python -m clawcat.cli "做个每日AI新闻"
python -m clawcat.cli "今天A股怎么样"
python -m clawcat.cli "OCR技术周报，重点关注大厂开源动态和竞品分析"
```

## 目录结构

```
clawcat/
  adapters/              # 数据源适配器 + registry.json
    news/                # 新闻类（36kr, wallstreetcn, weibo, tencent, v2ex, cn_economy, rss）
    finance/             # 金融类（akshare_stock, akshare_macro）
    tech/                # 技术类（github_trending, hackernews, arxiv, hf_papers）
    search/              # 搜索引擎（duckduckgo, baidu）
  nodes/                 # LangGraph 节点（14 个，每个文件一个节点）
  grounding/             # 质量检查器（6 个）
  prompts/               # LLM 提示词模板
  schema/                # Pydantic 模型（Brief, TaskConfig, Item, UserProfile）
  templates/             # Jinja2 HTML 模板
  static/                # 静态资源
  utils/                 # 工具模块
  graph.py               # LangGraph StateGraph 定义
  state.py               # Pipeline 状态 TypedDict
  config.py              # pydantic-settings 配置
  llm.py                 # instructor 客户端工厂
  cli.py                 # CLI 入口
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

## License

MIT

---

*Built by llx & Luna 🐱 — where the claw meets the code.* 🦞
