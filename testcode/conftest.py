"""Shared fixtures and pytest markers for ClawCat test suite."""

import pytest
from datetime import datetime, timedelta

from clawcat.schema.item import Item
from clawcat.schema.task import TaskConfig, SourceSelection, SectionPlan
from clawcat.schema.brief import (
    Brief, BriefSection, BriefItem, BriefMetadata, TimeRange, ClawComment,
)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests that call real LLM / network (deselect with '-m not slow')")
    config.addinivalue_line("markers", "network: marks tests that require internet access")


@pytest.fixture
def mock_items():
    now = datetime.now()
    return [
        Item(
            title="OpenAI 发布 GPT-5",
            source="hackernews",
            url="https://openai.com/gpt5",
            raw_text="OpenAI 今日发布 GPT-5，性能提升 10 倍。股价上涨 15%。融资额达 50 亿美元。",
            published_at=(now - timedelta(hours=6)).isoformat(),
        ),
        Item(
            title="腾讯 Q4 财报超预期",
            source="36kr",
            url="https://36kr.com/p/123",
            raw_text="腾讯 2026 年 Q4 营收 1500 亿元，同比增长 12%。净利润 380 亿元。",
            published_at=(now - timedelta(hours=12)).isoformat(),
        ),
        Item(
            title="上证指数收涨",
            source="akshare",
            url="",
            raw_text="上证指数收于 3913.42 点，涨幅 1.2%。深证成指报 11523.67 点。",
            published_at=(now - timedelta(hours=3)).isoformat(),
        ),
    ]


@pytest.fixture
def mock_task_config():
    now = datetime.now()
    return TaskConfig(
        topic="AI 技术",
        report_title="AI 技术 · 今日速递",
        period="daily",
        focus_areas=["大模型发布", "科技公司财报", "A 股市场"],
        tone="professional",
        target_audience="技术决策者",
        since=(now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00"),
        until=now.isoformat(),
        max_items=30,
        selected_sources=[
            SourceSelection(source_name="hackernews", reason="全球科技新闻"),
            SourceSelection(source_name="36kr", reason="中国科技媒体"),
        ],
        report_structure=[
            SectionPlan(heading="焦点头条", section_type="hero", suggested_item_count=2),
            SectionPlan(heading="行业动态", section_type="items", suggested_item_count=3),
            SectionPlan(heading="Claw 锐评", section_type="review", suggested_item_count=2),
        ],
    )


@pytest.fixture
def mock_brief():
    now = datetime.now()
    return Brief(
        report_type="daily",
        title="AI 技术 · 今日速递",
        issue_label=now.strftime("%Y-%m-%d"),
        time_range=TimeRange(
            user_requested="过去24小时",
            resolved_start=(now - timedelta(days=1)).isoformat(),
            resolved_end=now.isoformat(),
            report_generated=now.isoformat(),
        ),
        executive_summary="GPT-5 发布标志着大模型进入新阶段，腾讯财报超预期验证 AI 商业化加速。",
        sections=[
            BriefSection(
                heading="焦点头条",
                section_type="hero",
                prose="本日最重大事件集中在 AI 基础设施层面。",
                items=[
                    BriefItem(
                        title="GPT-5 正式发布",
                        summary="OpenAI 发布 GPT-5，性能提升 10 倍，定价下降 40%。",
                        key_facts=["性能提升: 10倍", "定价: 下降40%"],
                        verdict="大模型竞争进入性价比阶段",
                        sources=["hackernews"],
                    ),
                ],
            ),
            BriefSection(
                heading="行业动态",
                section_type="items",
                items=[
                    BriefItem(
                        title="腾讯 Q4 财报超预期",
                        summary="腾讯 Q4 营收 1500 亿元，净利润 380 亿元。",
                        key_facts=["营收: 1500亿元", "净利润: 380亿元", "增长: 12%"],
                        sources=["36kr"],
                    ),
                ],
            ),
            BriefSection(
                heading="Claw 锐评",
                section_type="review",
                items=[
                    BriefItem(
                        title="GPT-5 的真正影响",
                        summary="GPT-5 不仅是性能升级，更是商业模式重塑。",
                        claw_comment=ClawComment(
                            highlight="降价 40% 是杀手锏",
                            concerns=["开源替代品跟进速度", "算力成本转嫁问题"],
                            verdict="短期利好应用层，长期挤压中小模型厂商",
                        ),
                        sources=["hackernews"],
                    ),
                ],
            ),
        ],
        metadata=BriefMetadata(
            llm_model="qwen3.5-plus",
            sources_used=["hackernews", "36kr"],
            items_fetched=50,
            items_selected=10,
        ),
    )


@pytest.fixture
def mock_summaries():
    return [
        {
            "title": "OpenAI 发布 GPT-5",
            "summary": "OpenAI 今日发布 GPT-5，性能提升 10 倍，定价下降 40%。",
            "key_facts": ["性能提升: 10倍", "定价: 下降40%", "融资额: 50亿美元", "股价涨幅: 15%"],
            "source": "hackernews",
            "url": "https://openai.com/gpt5",
        },
        {
            "title": "腾讯 Q4 财报超预期",
            "summary": "腾讯 2026 年 Q4 营收 1500 亿元，同比增长 12%，净利润 380 亿元。",
            "key_facts": ["营收: 1500亿元", "增长: 12%", "净利润: 380亿元"],
            "source": "36kr",
            "url": "https://36kr.com/p/123",
        },
        {
            "title": "上证指数收涨",
            "summary": "上证指数收于 3913.42 点，涨幅 1.2%。深证成指报 11523.67 点。",
            "key_facts": ["上证指数: 3913.42点", "涨幅: 1.2%", "深证成指: 11523.67点"],
            "source": "akshare",
            "url": "",
        },
    ]
