"""AKShare stock adapter — A-share / HK / US market data via akshare."""

from __future__ import annotations

from datetime import datetime

from clawcat.adapters.base import make_result
from clawcat.schema.item import FetchResult, Item


async def fetch(
    since: datetime,
    until: datetime,
    config: dict | None = None,
) -> FetchResult:
    items: list[Item] = []

    try:
        import asyncio
        import akshare as ak

        df = await asyncio.to_thread(ak.stock_zh_index_spot_em)
        if df is not None and not df.empty:
            for _, row in df.head(10).iterrows():
                name = row.get("名称", "")
                code = row.get("代码", "")
                current = row.get("最新价", "")
                change_pct = row.get("涨跌幅", 0)
                if not name:
                    continue
                sign = "+" if change_pct and float(change_pct) > 0 else ""
                items.append(Item(
                    title=f"{name}({code}) {sign}{change_pct}%",
                    url=f"https://quote.eastmoney.com/zs{code}.html",
                    source="akshare_stock",
                    raw_text=f"最新价: {current}, 涨跌幅: {sign}{change_pct}%",
                    published_at=datetime.now().isoformat(),
                    meta={
                        "code": str(code),
                        "price": str(current),
                        "change_pct": float(change_pct) if change_pct else 0,
                        "sub_source": "AKShare指数",
                    },
                ))
    except ImportError:
        pass
    except Exception:
        pass

    return make_result("akshare_stock", items, time_filtered=False)
