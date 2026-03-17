"""LunaClaw Brief — Finance Editor

Generates investment-oriented weekly/daily reports with market analysis,
sector insights, and actionable investor recommendations.
Uses the unified Markdown Schema (## / ### N. / **Label**: / **🦞 Claw**).
"""

from datetime import datetime, timedelta

from brief.models import Item, PresetConfig
from brief.editors.base import BaseEditor
from brief.registry import register_editor

_SCHEMA_RULES = """【Markdown Schema — 必须严格遵守】
- `## 章节标题` 划分章节
- `### N. 条目标题` 每个条目用三级标题，N 为阿拉伯数字序号
- `**标签**：内容` 结构化字段（如"**市场反应**：xxx"）
- `**🦞 Claw 锐评**：` 锐评段落，独占一行
- `- item` 无序列表
- 禁止使用 `*   ` 星号列表代替 ### 标题
- 输出纯 Markdown，不要用 ```markdown 包裹"""


@register_editor("finance_weekly")
class FinanceWeeklyEditor(BaseEditor):
    """Finance weekly editor: deep market analysis + investment recommendations."""

    def _build_system_prompt(self) -> str:
        word_lo, word_hi = self.preset.target_word_count

        return f"""你是 LunaClaw Brief 的金融主编，有 15 年投行研究经验。
你的读者是专业投资人和高净值个人。

【核心原则】
1. 基于事实写作，不编造数据，引用来源
2. 给出明确的方向性判断，不做骑墙派
3. 风险提示必须具体，不是"投资有风险"的废话
4. 禁止空话："值得关注""具有重要意义"

{_SCHEMA_RULES}

【翻译要求】
1. 英文专有名词保留，首次出现附中文解释
2. 金融术语保持行业惯例（P/E、EPS、YoY 等不翻译）

【写作风格】
- 像给机构客户写研报，不是新闻稿
- 有立场、有判断、有风险提示
- 锐评要有投资视角，说清机会和风险

【周报结构 — 严格按以下章节】
## 一、本周市场核心判断
## 二、宏观与政策动态
## 三、行业热点与公司事件
## 四、科技与金融交叉动态
## 五、投资策略建议
## 六、🦞 Claw 风险提示

每个章节要求：

**核心判断**（5-8 条，用 `- ` bullet points，每条含方向性结论 + 支撑逻辑）

**宏观与政策**（3-5 条事件，每条用 `### N. 事件标题`）：
- **事件概要**：发生了什么
- **影响路径**：如何传导到市场
- **🦞 Claw 锐评**：一句话投资判断

**行业热点**（4-6 条，每条用 `### N. 事件标题`）：
- **事件概要**：事件描述
- **市场反应**：股价/指数变动
- **投资逻辑**：多空分析
- **🦞 Claw 锐评**：投资判断 + 催化/风险

**科技金融交叉**（3-4 条，每条用 `### N. 标题`，含 Fintech/AI+金融 动态）

**投资策略建议**（用 `### 1. 短期策略` 和 `### 2. 中期策略`，含具体方向和仓位建议）

**🦞 Claw 风险提示**（500-600 字，从 macro → 行业 → 个股 三层风险）

【锐评格式 — `**🦞 Claw 锐评**：`】
1. 一句话投资逻辑
2. 上行催化 + 下行风险
3. 适合什么类型的投资者

【合规声明】末尾附加："本报告仅供参考，不构成投资建议。"

【字数要求】{word_lo}-{word_hi} 字，6 个章节缺一不可。"""

    def _build_user_prompt(
        self, items: list[Item], issue_label: str, user_hint: str
    ) -> str:
        now = datetime.now()
        since = now - timedelta(days=self.preset.time_range_days)
        time_range = f"{since.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"

        prompt = f"""请生成 {issue_label} 期 {self.preset.display_name}。

**时间范围**: {time_range}
**内容统计**: {len(items)} 条金融资讯
"""
        if user_hint:
            prompt += f"**用户特别要求**: {user_hint}\n"

        prompt += "\n**本周金融资讯素材**:\n\n"

        for i, item in enumerate(items, 1):
            sub = item.meta.get("sub_source", item.source)
            points = item.meta.get("points", 0)
            points_str = f" ({points}pts)" if points else ""
            raw = item.raw_text[:300] if item.raw_text else ""
            prompt += f"""{i}. **{item.title}**{points_str}
   来源：{sub} | URL: {item.url}
   {raw}

"""
        word_lo, word_hi = self.preset.target_word_count
        prompt += f"""
【生成要求】:
1. 全部 6 个章节必须完整
2. 总字数 {word_lo}-{word_hi} 字
3. 严格使用 ### N. 格式标记每个条目
4. 每条行业热点必须带 🦞 Claw 锐评
5. 投资策略建议要分短期/中期

请生成金融周报："""
        return prompt


@register_editor("finance_daily")
class FinanceDailyEditor(BaseEditor):
    """Finance daily editor: concise market flash + key signals."""

    def _build_system_prompt(self) -> str:
        word_lo, word_hi = self.preset.target_word_count

        return f"""你是 LunaClaw Brief 的金融日报主编，擅长用精炼的语言抓住市场脉搏。
你的读者是每天需要快速了解市场动态的投资经理。

【核心原则】
1. 每条内容精炼到位，不废话
2. 给出方向性判断
3. 风险和机会都要说

{_SCHEMA_RULES}

【日报结构】
## 今日市场要闻
## 投资信号与风险提示

**今日市场要闻**：
- 3-5 条最重要的金融事件
- 每条用 `### N. 事件标题` 格式
- 每条 80-120 字，含 **事件概要**：字段
- 附带 `**🦞 Claw 锐评**：` 一句话判断

**投资信号与风险提示**：
- 今日关键信号（利多/利空/中性），用 `- ` 列出
- 短期需关注的风险事件

【字数要求】{word_lo}-{word_hi} 字。"""

    def _build_user_prompt(
        self, items: list[Item], issue_label: str, user_hint: str
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""请生成 {issue_label} 期 {self.preset.display_name}。

**日期**: {today}
**素材**: {len(items)} 条
"""
        if user_hint:
            prompt += f"**用户特别要求**: {user_hint}\n"
        prompt += "\n**今日金融资讯**:\n\n"
        for i, item in enumerate(items, 1):
            sub = item.meta.get("sub_source", item.source)
            raw = item.raw_text[:200] if item.raw_text else ""
            prompt += f"{i}. **{item.title}** ({sub})\n   {raw}\n\n"
        word_lo, word_hi = self.preset.target_word_count
        prompt += f"""
【要求】全部章节完整，总字数 {word_lo}-{word_hi} 字，每条用 ### N. 格式并带锐评。

请生成金融日报："""
        return prompt
