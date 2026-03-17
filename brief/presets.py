"""LunaClaw Brief — Preset Definitions

Each preset is a complete configuration for a report type.
Add new presets here and they become instantly available via CLI / Skill.

Available presets:
  - ai_cv_weekly     : AI/CV tech deep-dive weekly
  - ai_daily         : AI tech daily brief
  - finance_weekly   : Investment-oriented market weekly
  - finance_daily    : Market flash daily
  - stock_a_daily    : A-share market daily
  - stock_hk_daily   : HK stock market daily
  - stock_us_daily   : US stock market daily
"""

from pathlib import Path

import yaml

from brief.models import PresetConfig

# ────────────────────────────────────────────
# Tech — AI / CV
# ────────────────────────────────────────────

AI_CV_WEEKLY = PresetConfig(
    name="ai_cv_weekly",
    display_name="AI/CV Weekly",
    cycle="weekly",
    editor_type="tech_weekly",
    topic="ai",
    sources=["github", "arxiv", "hackernews", "paperswithcode"],
    time_range_days=7,
    max_items=25,
    domain_keywords={
        "ocr": 5, "document ai": 5, "document understanding": 5,
        "layout analysis": 5, "text recognition": 5,
        "computer vision": 4, "cv": 4, "multimodal": 4,
        "vlm": 4, "vision-language": 4,
        "detection": 3, "segmentation": 3, "image": 3,
        "vision": 3, "medical imaging": 3,
    },
    source_weights={"arxiv": 2, "github": 1, "hackernews": 1, "paperswithcode": 2},
    low_value_keywords=[
        "crypto", "nft", "blockchain", "portfolio", "resume",
        "personal website", "job posting", "hiring", "awesome list",
    ],
    sections=[
        "core_conclusions", "events", "projects", "papers", "trends", "review",
    ],
    target_word_count=(4000, 5500),
    tone="sharp",
    min_sections=5,
    min_word_count=3500,
    dedup_window_days=30,
    template="report",
    description="AI/CV/多模态技术周报，包含开源项目推荐、论文推荐、趋势分析等",
)

AI_DAILY = PresetConfig(
    name="ai_daily",
    display_name="AI Daily Brief",
    cycle="daily",
    editor_type="tech_daily",
    topic="ai",
    sources=["github", "arxiv", "hackernews"],
    time_range_days=1,
    max_items=10,
    domain_keywords={
        "llm": 3, "agent": 3, "multimodal": 3,
        "cv": 2, "ocr": 2, "vision": 2,
        "transformer": 2, "diffusion": 2,
    },
    source_weights={"hackernews": 2, "arxiv": 1, "github": 1},
    low_value_keywords=[
        "crypto", "nft", "blockchain", "portfolio", "resume",
    ],
    sections=["top_picks", "quick_takes"],
    target_word_count=(800, 1500),
    tone="sharp",
    min_sections=2,
    min_word_count=600,
    dedup_window_days=3,
    template="report",
    description="AI 技术日报，快速了解当天最重要的 AI 技术动态",
)

# ────────────────────────────────────────────
# Finance — Securities & Investment
# ────────────────────────────────────────────

FINANCE_WEEKLY = PresetConfig(
    name="finance_weekly",
    display_name="LunaClaw Finance Weekly",
    cycle="weekly",
    editor_type="finance_weekly",
    topic="finance",
    sources=["finnews", "hackernews", "yahoo_finance"],
    time_range_days=7,
    max_items=20,
    domain_keywords={
        "earnings": 5, "revenue": 5, "ipo": 5, "fundraising": 5,
        "valuation": 4, "stock": 4, "market": 4, "fed": 4,
        "interest rate": 4, "gdp": 4,
        "fintech": 3, "payment": 3, "banking": 3,
        "venture capital": 3, "private equity": 3,
        "ai investment": 3, "semiconductor": 3,
    },
    source_weights={"finnews": 2, "hackernews": 1, "yahoo_finance": 2},
    low_value_keywords=[
        "meme", "shitcoin", "pump", "moon", "fomo",
    ],
    sections=[
        "core_judgment", "macro_policy", "sector_events",
        "tech_finance", "strategy", "risk",
    ],
    target_word_count=(4000, 5500),
    tone="sharp",
    min_sections=5,
    min_word_count=3500,
    dedup_window_days=14,
    template="report",
    description="金融投资周报，宏观分析、行业热点、投资策略建议",
    show_disclaimer=True,
)

FINANCE_DAILY = PresetConfig(
    name="finance_daily",
    display_name="LunaClaw Finance Daily",
    cycle="daily",
    editor_type="finance_daily",
    topic="finance",
    sources=["finnews", "hackernews", "yahoo_finance"],
    time_range_days=1,
    max_items=10,
    domain_keywords={
        "earnings": 4, "stock": 4, "market": 4,
        "fed": 3, "interest rate": 3,
        "fintech": 2, "ipo": 2,
    },
    source_weights={"finnews": 2, "hackernews": 1, "yahoo_finance": 2},
    low_value_keywords=["meme", "shitcoin", "pump"],
    sections=["market_news", "signals"],
    target_word_count=(800, 1500),
    tone="sharp",
    min_sections=2,
    min_word_count=600,
    dedup_window_days=3,
    template="report",
    description="金融快报日刊，每日市场要闻和投资信号",
    show_disclaimer=True,
)

# ────────────────────────────────────────────
# Stock — Regional Market Briefs
# ────────────────────────────────────────────

STOCK_A_DAILY = PresetConfig(
    name="stock_a_daily",
    display_name="LunaClaw A股日报",
    cycle="daily",
    editor_type="stock_a",
    topic="stock_a",
    sources=["eastmoney", "xueqiu", "finnews"],
    time_range_days=1,
    max_items=15,
    domain_keywords={
        "a股": 5, "沪深": 5, "上证": 5, "深证": 5, "创业板": 5,
        "科创板": 5, "北交所": 5, "沪深300": 5,
        "北向资金": 4, "融资融券": 4, "涨停": 4, "板块轮动": 4,
        "china stock": 4, "shanghai": 4, "shenzhen": 4, "csi 300": 4,
        "a-share": 4, "chinese market": 4,
        "央行": 3, "lpr": 3, "gdp": 3, "pmi": 3,
        "semiconductor": 3, "新能源": 3, "光伏": 3,
    },
    source_weights={"eastmoney": 3, "xueqiu": 2, "finnews": 1},
    low_value_keywords=["meme", "shitcoin", "pump", "nft"],
    sections=["market_trend", "sector_focus", "capital_flow", "ipo_alert", "strategy_risk"],
    target_word_count=(1500, 2500),
    tone="sharp",
    min_sections=3,
    min_word_count=1200,
    dedup_window_days=3,
    template="report",
    description="A股沪深市场日报，大盘走势、板块轮动、北向资金、新股打新、异动分析",
    show_disclaimer=True,
)

STOCK_HK_DAILY = PresetConfig(
    name="stock_hk_daily",
    display_name="LunaClaw 港股日报",
    cycle="daily",
    editor_type="stock_hk",
    topic="stock_hk",
    sources=["finnews", "yahoo_finance", "xueqiu"],
    time_range_days=1,
    max_items=15,
    domain_keywords={
        "港股": 5, "恒生": 5, "恒指": 5, "hkex": 5, "hang seng": 5,
        "南向资金": 5, "港股通": 5, "h-share": 5,
        "hong kong stock": 4, "alibaba": 4, "tencent": 4,
        "meituan": 4, "jd": 4, "中概股": 4, "adr": 4,
        "联汇制度": 3, "离岸人民币": 3, "恒生科技": 3,
    },
    source_weights={"finnews": 2, "yahoo_finance": 2, "xueqiu": 1},
    low_value_keywords=["meme", "shitcoin", "pump", "nft"],
    sections=["core_judgment", "sector_focus", "cross_market", "ipo_alert", "strategy_risk"],
    target_word_count=(1500, 2500),
    tone="sharp",
    min_sections=3,
    min_word_count=1200,
    dedup_window_days=3,
    template="report",
    description="港股日报，恒生指数、南向资金、中概股、港股IPO、跨市场联动",
    show_disclaimer=True,
)

STOCK_US_DAILY = PresetConfig(
    name="stock_us_daily",
    display_name="LunaClaw 美股日报",
    cycle="daily",
    editor_type="stock_us",
    topic="stock_us",
    sources=["yahoo_finance", "finnews"],
    time_range_days=1,
    max_items=15,
    domain_keywords={
        "s&p 500": 5, "nasdaq": 5, "dow jones": 5, "nyse": 5,
        "us stock": 5, "wall street": 5, "fed": 5,
        "apple": 4, "nvidia": 4, "microsoft": 4, "google": 4,
        "tesla": 4, "amazon": 4, "meta": 4,
        "interest rate": 4, "treasury yield": 4, "vix": 4,
        "earnings": 4, "ipo": 4,
        "semiconductor": 3, "ai chip": 3, "biotech": 3,
    },
    source_weights={"yahoo_finance": 2, "finnews": 2},
    low_value_keywords=["meme", "shitcoin", "pump", "nft"],
    sections=["core_judgment", "tech_stocks", "macro_policy", "ipo_alert", "strategy_risk"],
    target_word_count=(1500, 2500),
    tone="sharp",
    min_sections=3,
    min_word_count=1200,
    dedup_window_days=3,
    template="report",
    description="美股日报，S&P/NASDAQ走势、科技巨头、Fed政策、IPO预报、期权信号",
    show_disclaimer=True,
)

# ────────────────────────────────────────────
# Registry
# ────────────────────────────────────────────

PRESETS: dict[str, PresetConfig] = {
    "ai_cv_weekly": AI_CV_WEEKLY,
    "ai_daily": AI_DAILY,
    "finance_weekly": FINANCE_WEEKLY,
    "finance_daily": FINANCE_DAILY,
    "stock_a_daily": STOCK_A_DAILY,
    "stock_hk_daily": STOCK_HK_DAILY,
    "stock_us_daily": STOCK_US_DAILY,
}


def _load_custom_presets() -> dict[str, PresetConfig]:
    """Load user-defined custom presets from data/custom_presets/*.yaml."""
    custom_dir = Path(__file__).parent.parent / "data" / "custom_presets"
    custom: dict[str, PresetConfig] = {}
    if not custom_dir.exists():
        return custom
    for yaml_file in sorted(custom_dir.glob("*.yaml")):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict) and "name" in data:
                preset = PresetConfig(**data)
                custom[preset.name] = preset
        except Exception as e:
            print(f"[warn] Failed to load custom preset {yaml_file.name}: {e}")
    return custom


# Load custom presets on import
_custom = _load_custom_presets()
PRESETS.update(_custom)


def get_preset(name: str) -> PresetConfig:
    """Look up a preset by name. Raises ValueError if not found."""
    if name not in PRESETS:
        raise ValueError(
            f"Unknown preset '{name}'. Available: {list(PRESETS.keys())}"
        )
    return PRESETS[name]
