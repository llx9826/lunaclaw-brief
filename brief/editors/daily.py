"""LunaClaw Brief — Tech Daily Editor

Generates concise daily tech briefs using the unified Markdown Schema.
"""

from datetime import datetime

from brief.models import Item, PresetConfig
from brief.editors.base import BaseEditor
from brief.registry import register_editor

_SCHEMA_RULES = """【Markdown Schema — 必须严格遵守】
- `## 章节标题` 划分章节
- `### N. 条目标题` 每个条目用三级标题，N 为阿拉伯数字序号
- `**标签**：内容` 结构化字段
- `**🦞 Claw 锐评**：` 锐评段落，独占一行
- `- item` 无序列表
- 禁止使用 `*   ` 星号列表代替 ### 标题
- 输出纯 Markdown，不要用 ```markdown 包裹"""


@register_editor("tech_daily")
class DailyEditor(BaseEditor):
    """Tech daily editor: concise daily brief with sharp one-liner reviews."""

    def _build_system_prompt(self) -> str:
        word_lo, word_hi = self.preset.target_word_count

        return f"""你是 LunaClaw Brief 的日报主编，擅长用简洁有力的文字概括技术动态。

【核心原则】
1. 基于真实数据写作，不编造
2. 每条内容精炼到位，不废话
3. 锐评一针见血，不和稀泥

{_SCHEMA_RULES}

【日报结构 — 严格按照以下章节】
## 今日必看
## 快评

**今日必看**：
- 挑选 3-5 条最值得关注的内容
- 每条用 `### N. 标题` 格式
- 每条 80-120 字，用 **内容概要**：字段说清是什么、为什么重要
- 每条附带 `**🦞 Claw 锐评**：` 一句话点评（30-50 字，必须有立场）

**快评**：
- 对今日整体动态的 200-300 字总结
- 点出趋势和值得警惕的信号

【锐评要求】
- 一句话即可，但必须有态度
- 禁止空话："值得关注""具有重要意义"

【字数要求】总字数 {word_lo}-{word_hi} 字。"""

    def _build_user_prompt(
        self, items: list[Item], issue_label: str, user_hint: str
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""请生成 {issue_label} 期 {self.preset.display_name}。

**日期**: {today}
**素材数量**: {len(items)} 条
"""
        if user_hint:
            prompt += f"**用户特别要求**: {user_hint}\n"

        prompt += "\n**今日内容**:\n\n"

        for i, item in enumerate(items, 1):
            tags = ", ".join(item.meta.get("domain_tags", []))
            raw = item.raw_text[:200] if item.raw_text else ""
            prompt += f"""{i}. **{item.title}**
   来源：{item.source} | 领域：{tags}
   {raw}

"""

        word_lo, word_hi = self.preset.target_word_count
        prompt += f"""
【生成要求】:
1. 必须包含"今日必看"和"快评"两个章节
2. 今日必看用 ### N. 格式，挑 3-5 条最重要的，每条带锐评
3. 总字数 {word_lo}-{word_hi} 字
4. 简洁有力，不要凑字数

请生成日报："""
        return prompt
