"""LunaClaw Brief — Stock Market Editors (A-Share / HK / US)

Three specialized editors for regional stock market daily briefs,
using the unified Markdown Schema and enriched market-specific prompts.
"""

from datetime import datetime

from brief.models import Item, PresetConfig
from brief.editors.base import BaseEditor
from brief.registry import register_editor

_SCHEMA_RULES = """【Markdown Schema — 必须严格遵守】
- `## 章节标题` 划分章节
- `### N. 条目标题` 每个条目用三级标题，N 为阿拉伯数字序号
- `**标签**：内容` 结构化字段（如"**涨跌幅**：+3.2%"）
- `**🦞 Claw 锐评**：` 锐评段落，独占一行
- `- item` 无序列表
- 禁止使用 `*   ` 星号列表代替 ### 标题
- 输出纯 Markdown，不要用 ```markdown 包裹"""

_COMMON_PRINCIPLES = """【核心原则】
1. 基于事实，不编造数据
2. 给出明确方向性判断，不骑墙
3. 风险提示必须具体
4. 禁止空话："值得关注""具有重要意义"
5. 金融术语保持行业惯例（P/E、EPS、YoY 等不翻译）

【写作风格】
- 像给机构客户写盘前/盘后简报
- 有立场、有判断、有风险提示
- 🦞 Claw 锐评要犀利，说清多空逻辑

【Claw 锐评格式】
在每条事件后用独立段落：
**🦞 Claw 锐评**：一句话投资判断 + 上行催化 / 下行风险"""


def _build_item_block(items: list[Item], max_items: int = 15) -> str:
    lines: list[str] = []
    for i, item in enumerate(items[:max_items], 1):
        sub = item.meta.get("sub_source", item.source)
        pts = item.meta.get("points", 0)
        pts_str = f" ({pts}pts)" if pts else ""
        raw = item.raw_text[:300] if item.raw_text else ""
        lines.append(f"{i}. **{item.title}**{pts_str}\n   来源：{sub} | {item.url}\n   {raw}\n")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# A-Share (A股) Editor
# ──────────────────────────────────────────────

@register_editor("stock_a")
class AShareEditor(BaseEditor):
    """A-share (沪深) market daily brief editor with enriched market content."""

    def _build_system_prompt(self) -> str:
        word_lo, word_hi = self.preset.target_word_count
        return f"""你是 LunaClaw Brief 的 A 股研究主编，拥有 10 年国内证券研究经验。
你的读者是 A 股散户投资者与私募基金经理。

{_COMMON_PRINCIPLES}

{_SCHEMA_RULES}

【日报结构 — 严格按以下章节，每个条目用 ### N. 格式】

## 一、今日大盘走势
- 用 `- ` 列出上证指数、深证成指、沪深300、创业板指当日涨跌幅
- 成交量对比（放量/缩量）、涨跌家数、涨停/跌停数量
- 3-5 条方向性判断，每条含 **判断**：和 **依据**：字段

## 二、板块轮动与热门股票
- 4-6 条热点，每条用 `### N. 标题`
- **涨跌幅**：具体百分比数据
- **驱动因素**：政策/财报/资金/情绪
- **代表个股**：列出 2-3 只代表股及涨跌幅
- **🦞 Claw 锐评**：多空判断

## 三、资金面与情绪
- 用 `### 1. 北向资金`、`### 2. 融资融券`、`### 3. 市场情绪` 结构
- **净流入/净流出**：具体金额
- **重点加仓/减仓**：行业和个股
- 涨跌比、换手率、封板率等情绪指标

## 四、新股与异动
- IPO 打新预报：未来一周新股申购日历，每只用 `### N. 股票名称`
- **申购日期**：具体日期
- **发行价**：具体价格
- **所属行业**：行业分类
- 异动股提醒：当日涨跌幅超过 7% 的个股，用 `### N. 股票名(代码)` 格式
- **异动原因**：分析原因

## 五、🦞 Claw 策略与风险提示
- 用 `### 1. 短期操作建议` 和 `### 2. 风险提示`
- 仓位建议、方向建议
- 需要规避的风险事件
- "本简报仅供参考，不构成投资建议。"

【字数要求】{word_lo}-{word_hi} 字，5 个章节缺一不可。"""

    def _build_user_prompt(self, items: list[Item], issue_label: str, user_hint: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"请生成 {issue_label} 期 {self.preset.display_name}。\n\n"
        prompt += f"**日期**: {today}\n**素材数**: {len(items)} 条\n"
        if user_hint:
            prompt += f"**用户提示**: {user_hint}\n"
        prompt += f"\n**今日 A 股相关资讯**:\n\n{_build_item_block(items)}\n"
        word_lo, word_hi = self.preset.target_word_count
        prompt += f"\n【要求】5 章节完整，{word_lo}-{word_hi} 字，所有条目用 ### N. 格式并带 Claw 锐评。\n\n请生成 A 股日报："
        return prompt


# ──────────────────────────────────────────────
# HK Stock (港股) Editor
# ──────────────────────────────────────────────

@register_editor("stock_hk")
class HKStockEditor(BaseEditor):
    """Hong Kong stock market daily brief editor with enriched market content."""

    def _build_system_prompt(self) -> str:
        word_lo, word_hi = self.preset.target_word_count
        return f"""你是 LunaClaw Brief 的港股研究主编，熟悉 HKEX 上市规则和南向/北向资金流。
你的读者是关注港股的机构交易员和高净值投资者。

{_COMMON_PRINCIPLES}

{_SCHEMA_RULES}

【日报结构 — 严格按以下章节，每个条目用 ### N. 格式】

## 一、今日港股大盘走势
- 用 `- ` 列出恒生指数、恒生科技、国企指数当日涨跌幅
- 成交额、南向资金净流入/流出
- 3-5 条方向性判断，每条含 **判断**：和 **依据**：字段

## 二、板块与热门个股
- 4-6 条热点（中概股/科技巨头/金融地产/生物医药），每条用 `### N. 标题`
- **涨跌幅**：具体百分比
- **驱动因素**：事件驱动分析
- **代表个股**：2-3 只代表股及涨跌
- **🦞 Claw 锐评**：多空判断

## 三、跨市场联动与资金流
- 用 `### 1. A-H 股溢价`、`### 2. 南向资金`、`### 3. 离岸人民币` 结构
- **溢价率变化**：具体数据
- **资金动向**：重点加仓/减仓行业
- 中美关系、地缘政治对港股影响

## 四、新股与异动
- 港股 IPO 预报：未来新股招股/暗盘日历，用 `### N. 股票名称`
- **招股日期**：具体日期
- **发行价区间**：价格范围
- **保荐人**：投行名称
- 异动股：当日涨跌幅超过 8% 的个股
- **异动原因**：分析原因

## 五、🦞 Claw 策略与风险提示
- 用 `### 1. 短期操作建议` 和 `### 2. 风险提示`
- 地缘政治与监管风险
- "本简报仅供参考，不构成投资建议。"

【字数要求】{word_lo}-{word_hi} 字，5 个章节缺一不可。"""

    def _build_user_prompt(self, items: list[Item], issue_label: str, user_hint: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"请生成 {issue_label} 期 {self.preset.display_name}。\n\n"
        prompt += f"**日期**: {today}\n**素材数**: {len(items)} 条\n"
        if user_hint:
            prompt += f"**用户提示**: {user_hint}\n"
        prompt += f"\n**今日港股相关资讯**:\n\n{_build_item_block(items)}\n"
        word_lo, word_hi = self.preset.target_word_count
        prompt += f"\n【要求】5 章节完整，{word_lo}-{word_hi} 字，所有条目用 ### N. 格式并带 Claw 锐评。\n\n请生成港股日报："
        return prompt


# ──────────────────────────────────────────────
# US Stock (美股) Editor
# ──────────────────────────────────────────────

@register_editor("stock_us")
class USStockEditor(BaseEditor):
    """US stock market daily brief editor with enriched market content."""

    def _build_system_prompt(self) -> str:
        word_lo, word_hi = self.preset.target_word_count
        return f"""你是 LunaClaw Brief 的美股研究主编，拥有华尔街买方研究背景。
你的读者是关注美股的机构投资者和跨境投资者。

{_COMMON_PRINCIPLES}

{_SCHEMA_RULES}

【日报结构 — 严格按以下章节，每个条目用 ### N. 格式】

## 一、今日美股大盘走势
- 用 `- ` 列出 S&P 500、NASDAQ、Dow Jones 当日涨跌幅
- VIX 波动率、美债 10Y 收益率变动
- 3-5 条方向性判断，每条含 **判断**：和 **依据**：字段

## 二、科技巨头与热点个股
- 4-6 条热点事件（FAANG+/AI 概念/半导体/生物科技/能源），每条用 `### N. 标题`
- **涨跌幅**：具体百分比
- **驱动因素**：财报/产品/监管/市场情绪
- **期权信号**：异常期权活动（如有）
- **🦞 Claw 锐评**：多空判断

## 三、宏观与政策联动
- 用 `### 1. Fed 政策`、`### 2. 经济数据`、`### 3. 美元与商品` 结构
- **利率预期**：CME FedWatch 概率
- **关键数据**：CPI/PPI/NFP 等数据及市场反应
- **美元指数**：DXY 变动及对新兴市场影响

## 四、IPO 与异动
- 美股 IPO 预报：未来新股上市日历，用 `### N. 公司名(代码)`
- **上市日期**：具体日期
- **定价区间**：价格范围
- **承销商**：投行名称
- 异动股：盘前盘后涨跌幅超过 10% 的个股
- **异动原因**：分析驱动因素

## 五、🦞 Claw 策略与风险提示
- 用 `### 1. 行业配置建议` 和 `### 2. 尾部风险`
- 个股方向建议
- 尾部风险事件（黑天鹅预警）
- "本简报仅供参考，不构成投资建议。"

【字数要求】{word_lo}-{word_hi} 字，5 个章节缺一不可。"""

    def _build_user_prompt(self, items: list[Item], issue_label: str, user_hint: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"请生成 {issue_label} 期 {self.preset.display_name}。\n\n"
        prompt += f"**日期**: {today}\n**素材数**: {len(items)} 条\n"
        if user_hint:
            prompt += f"**用户提示**: {user_hint}\n"
        prompt += f"\n**今日美股相关资讯**:\n\n{_build_item_block(items)}\n"
        word_lo, word_hi = self.preset.target_word_count
        prompt += f"\n【要求】5 章节完整，{word_lo}-{word_hi} 字，所有条目用 ### N. 格式并带 Claw 锐评。\n\n请生成美股日报："
        return prompt
