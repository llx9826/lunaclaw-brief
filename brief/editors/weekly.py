"""LunaClaw Brief — Tech Weekly Editor

Generates structured, in-depth weekly tech reports using the unified
Markdown Schema (## sections, ### numbered items, **Label**: fields).
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
- `- item` 无序列表（bullet points）
- 普通文本直接写段落
- 禁止使用 `*   ` 星号列表代替 ### 标题
- 输出纯 Markdown，不要用 ```markdown 包裹"""


@register_editor("tech_weekly")
class WeeklyEditor(BaseEditor):
    """Tech weekly editor: deep report with comparisons and sharp reviews."""

    def _build_system_prompt(self) -> str:
        p = self.preset
        domain_hint = "CV/OCR/多模态 AI" if "ai_cv" in p.name else "AI 技术"
        word_lo, word_hi = p.target_word_count

        return f"""你是 LunaClaw Brief 的主编，有 10 年科技媒体经验，专注于{domain_hint}领域。

【核心原则】
1. 基于真实数据写作，不编造内容
2. 信息不足就说"需要进一步观察"
3. 禁止空话："值得关注""具有重要意义""推动行业发展"
4. 禁止模板化表达

{_SCHEMA_RULES}

【翻译要求】
1. 除专有名词外，所有内容翻译成中文
2. 专有名词保留英文，首次出现时附中文解释
3. GitHub 项目介绍翻译成流畅中文
4. 论文摘要翻译成学术中文

【写作风格】
- 像给同行讲解，不是填模板
- 可以有观点、有判断、有批判
- 锐评要有锋芒，说明潜在问题
- 每个项目/论文的介绍要有实质内容，不是一句话概括

【周报结构 — 严格按照以下章节】
## 一、本周核心结论
## 二、本周重点事件
## 三、开源项目推荐（含竞品对比）
## 四、论文推荐
## 五、本周趋势分析
## 六、🦞 Claw 复盘

每个章节的内容要求：

**核心结论**（5-8 条，用 `- ` bullet points，每条 60-100 字，带数据或具体项目名支撑）

**重点事件**（4-6 条，每条用 `### N. 事件标题`，含以下字段）：
- **事件概要**：发生了什么
- **背景脉络**：为什么重要（技术 or 产业）
- **实际影响**：对开发者/企业意味着什么

**开源项目推荐**（4-6 个，每个用 `### N. 项目名`，含以下字段）：
- **是什么**：一句话定位
- **解决什么问题**：痛点 + 适用场景
- **技术亮点**：架构 / 算法 / 性能指标（需要具体数字）
- **竞品对比**：与 1-2 个同类项目比较优劣
- **🦞 Claw 锐评**：三段式

**论文推荐**（3-5 篇，每篇用 `### N. 论文标题`，含以下字段）：
- **研究问题**：解决什么问题
- **核心创新**：方法论突破在哪
- **实验结果**：关键指标
- **与前作对比**：相比之前的 SOTA 有什么进步
- **🦞 Claw 锐评**：三段式

**趋势分析**（4-6 条，用 `### N. 趋势标题`，每条 120-180 字，基于本周具体内容推导）

**🦞 Claw 复盘**（600-900 字，用 `### 1. 技术层`、`### 2. 产业层`、`### 3. 个人层`）

【锐评三段式 — 统一格式 `**🦞 Claw 锐评**：`】
1. 一句话亮点评价
2. 至少两点具体问题/局限/适用边界
3. 一句"适合谁/不适合谁"的明确判断

【字数要求】总字数 {word_lo}-{word_hi} 字，必须包含全部 6 个章节。"""

    def _build_user_prompt(
        self, items: list[Item], issue_label: str, user_hint: str
    ) -> str:
        now = datetime.now()
        since = now - timedelta(days=self.preset.time_range_days)
        time_range = f"{since.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"

        cv_count = sum(
            1 for i in items
            if "CV" in i.meta.get("domain_tags", []) or "OCR" in i.meta.get("domain_tags", [])
        )

        prompt = f"""请生成 {issue_label} 期 {self.preset.display_name}。

**时间范围**: {time_range}
**内容统计**: {len(items)} 条（CV/OCR 相关：{cv_count} 条）
"""
        if user_hint:
            prompt += f"**用户特别要求**: {user_hint}\n"

        prompt += "\n**本周素材（含竞品信息）**:\n\n"

        for i, item in enumerate(items, 1):
            tags = ", ".join(item.meta.get("domain_tags", []))
            stars = item.meta.get("stars", 0)
            stars_str = f" ⭐{stars}" if stars else ""
            raw = item.raw_text[:400] if item.raw_text else ""

            block = f"""{i}. **{item.title}**{stars_str}
   来源：{item.source} | 领域：{tags}
   {raw}
"""
            alternatives = item.meta.get("alternatives", [])
            if alternatives:
                block += "   **同类项目对比**:\n"
                for alt in alternatives:
                    alt_stars = alt.get("stars", 0)
                    alt_desc = alt.get("description", "")[:120]
                    block += f"   - {alt['name']} (⭐{alt_stars}): {alt_desc}\n"

            prompt += block + "\n"

        word_lo, word_hi = self.preset.target_word_count
        prompt += f"""
【生成要求】:
1. 必须包含全部 6 个章节，缺一不可
2. 总字数 {word_lo}-{word_hi} 字
3. 严格使用 ### N. 格式标记每个条目
4. 每个项目/论文必须带 🦞 Claw 锐评（三段式）
5. 复盘必须完整写完（技术层 + 产业层 + 个人层），不要截断
6. 直接输出 Markdown

请生成周报："""
        return prompt
