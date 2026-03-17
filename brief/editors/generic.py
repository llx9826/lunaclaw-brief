"""LunaClaw Brief — Generic Parameterized Editor

Fallback editor for topics without a specialized Editor subclass.
Generates prompts dynamically from PresetConfig fields (topic, cycle,
display_name, description, sections) so new report types can work
without writing a single line of Editor code.

Existing specialized editors (tech_weekly, finance_daily, stock_a, etc.)
remain untouched — this is only used when editor_type == "generic_daily"
or "generic_weekly".
"""

from datetime import datetime, timedelta

from brief.models import Item, PresetConfig
from brief.editors.base import BaseEditor
from brief.registry import register_editor

_SCHEMA_RULES = """【Markdown Schema — 必须严格遵守】
- `## 章节标题` 划分章节
- `### N. 条目标题` 每个条目用三级标题，N 为阿拉伯数字序号
- `**标签**：内容` 结构化字段（如"**事件概要**：xxx"）
- `**🦞 Claw 锐评**：` 锐评段落，独占一行
- `- item` 无序列表
- 禁止使用 `*   ` 星号列表代替 ### 标题
- 输出纯 Markdown，不要用 ```markdown 包裹"""


@register_editor("generic_daily")
class GenericDailyEditor(BaseEditor):
    """Topic-agnostic daily editor driven entirely by PresetConfig."""

    def _build_system_prompt(self) -> str:
        p = self.preset
        word_lo, word_hi = p.target_word_count
        topic_desc = p.description or p.display_name
        topic_name = p.topic or "综合"

        return f"""你是 LunaClaw Brief 的主编，专注于"{topic_name}"领域。
你的任务是生成一份高质量的日报。

【报告主题】{topic_desc}

【核心原则】
1. 基于真实数据写作，不编造内容
2. 每条内容精炼到位，不废话
3. 锐评一针见血，不和稀泥
4. 禁止空话："值得关注""具有重要意义"

{_SCHEMA_RULES}

【翻译要求】
1. 除专有名词外，所有内容翻译成中文
2. 专有名词保留英文，首次出现时附中文解释

【日报结构 — 严格按以下章节】
## 今日必看
## 深度解读
## 🦞 Claw 快评

**今日必看**：
- 挑选 3-5 条当日最值得关注的{topic_name}内容
- 每条用 `### N. 标题` 格式
- 每条含 **内容概要**：字段（80-120 字）
- 附带 `**🦞 Claw 锐评**：` 一句话点评

**深度解读**：
- 对 1-2 个关键事件进行深度分析（每个 150-250 字）
- 每个用 `### N. 标题` 格式
- 含 **背景脉络**：和 **实际影响**：字段

**🦞 Claw 快评**：
- 对今日整体动态的 200-300 字总结
- 点出趋势信号和值得警惕的风险

【字数要求】总字数 {word_lo}-{word_hi} 字。"""

    def _build_user_prompt(
        self, items: list[Item], issue_label: str, user_hint: str
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        p = self.preset

        prompt = f"""请生成 {issue_label} 期 {p.display_name}。

**日期**: {today}
**素材数量**: {len(items)} 条
"""
        if user_hint:
            prompt += f"**用户特别要求**: {user_hint}\n"

        prompt += "\n**今日内容素材**:\n\n"
        for i, item in enumerate(items, 1):
            tags = ", ".join(item.meta.get("domain_tags", []))
            raw = item.raw_text[:250] if item.raw_text else ""
            prompt += f"""{i}. **{item.title}**
   来源：{item.source} | 领域：{tags}
   {raw}

"""
        word_lo, word_hi = p.target_word_count
        prompt += f"""
【生成要求】:
1. 必须包含全部 3 个章节
2. 总字数 {word_lo}-{word_hi} 字
3. 严格使用 ### N. 格式标记每个条目
4. 每条必须带 🦞 Claw 锐评
5. 直接输出 Markdown

请生成日报："""
        return prompt


@register_editor("generic_weekly")
class GenericWeeklyEditor(BaseEditor):
    """Topic-agnostic weekly editor driven entirely by PresetConfig."""

    def _build_system_prompt(self) -> str:
        p = self.preset
        word_lo, word_hi = p.target_word_count
        topic_desc = p.description or p.display_name
        topic_name = p.topic or "综合"

        return f"""你是 LunaClaw Brief 的周报主编，专注于"{topic_name}"领域，有 10 年行业经验。
你的任务是生成一份深度周报。

【报告主题】{topic_desc}

【核心原则】
1. 基于真实数据写作，不编造内容
2. 信息不足就说"需要进一步观察"
3. 禁止空话："值得关注""具有重要意义"
4. 禁止模板化表达

{_SCHEMA_RULES}

【翻译要求】
1. 除专有名词外，所有内容翻译成中文
2. 专有名词保留英文，首次出现时附中文解释

【写作风格】
- 像给同行讲解，不是填模板
- 可以有观点、有判断、有批判
- 锐评要有锋芒，说明潜在问题

【周报结构 — 严格按以下章节】
## 一、本周核心结论
## 二、本周重点事件
## 三、深度分析
## 四、趋势展望
## 五、🦞 Claw 复盘

**核心结论**（5-8 条，用 `- ` bullet points，每条 60-100 字）

**重点事件**（4-6 条，每条用 `### N. 事件标题`）：
- **事件概要**：发生了什么
- **背景脉络**：为什么重要
- **实际影响**：意味着什么
- **🦞 Claw 锐评**：一句话点评

**深度分析**（2-3 篇，每篇用 `### N. 主题`，每篇 200-400 字的深度解读）

**趋势展望**（4-6 条，用 `### N. 趋势标题`，每条 120-180 字）

**🦞 Claw 复盘**（400-600 字，总结性分析 + 前瞻判断）

【锐评格式 — `**🦞 Claw 锐评**：`】
1. 一句话亮点评价
2. 具体问题/局限
3. 明确判断

【字数要求】总字数 {word_lo}-{word_hi} 字，必须包含全部 5 个章节。"""

    def _build_user_prompt(
        self, items: list[Item], issue_label: str, user_hint: str
    ) -> str:
        now = datetime.now()
        since = now - timedelta(days=self.preset.time_range_days)
        time_range = f"{since.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"
        p = self.preset

        prompt = f"""请生成 {issue_label} 期 {p.display_name}。

**时间范围**: {time_range}
**内容统计**: {len(items)} 条素材
"""
        if user_hint:
            prompt += f"**用户特别要求**: {user_hint}\n"

        prompt += "\n**本周素材**:\n\n"
        for i, item in enumerate(items, 1):
            tags = ", ".join(item.meta.get("domain_tags", []))
            raw = item.raw_text[:400] if item.raw_text else ""
            prompt += f"""{i}. **{item.title}**
   来源：{item.source} | 领域：{tags}
   {raw}

"""
        word_lo, word_hi = p.target_word_count
        prompt += f"""
【生成要求】:
1. 必须包含全部 5 个章节，缺一不可
2. 总字数 {word_lo}-{word_hi} 字
3. 严格使用 ### N. 格式标记每个条目
4. 每条重点事件必须带 🦞 Claw 锐评
5. 复盘必须完整写完，不要截断
6. 直接输出 Markdown

请生成周报："""
        return prompt
