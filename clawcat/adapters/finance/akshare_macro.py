"""AKShare macro adapter — Chinese macroeconomic data via akshare."""

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

        try:
            df = await asyncio.to_thread(ak.macro_china_pmi)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                date_val = latest.get("日期", latest.get("月份", ""))
                pmi = latest.get("制造业-Loss", latest.get("PMI", ""))
                items.append(Item(
                    title=f"中国制造业PMI: {pmi}",
                    url="https://data.eastmoney.com/cjsj/pmi.html",
                    source="akshare_macro",
                    raw_text=f"日期: {date_val}, PMI: {pmi}",
                    published_at=datetime.now().isoformat(),
                    meta={"indicator": "PMI", "sub_source": "AKShare宏观"},
                ))
        except Exception:
            pass

        try:
            df = await asyncio.to_thread(ak.macro_china_cpi)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                date_val = latest.get("日期", latest.get("月份", ""))
                cpi = latest.get("全国-当月", latest.get("CPI", ""))
                items.append(Item(
                    title=f"中国CPI: {cpi}",
                    url="https://data.eastmoney.com/cjsj/cpi.html",
                    source="akshare_macro",
                    raw_text=f"日期: {date_val}, CPI: {cpi}",
                    published_at=datetime.now().isoformat(),
                    meta={"indicator": "CPI", "sub_source": "AKShare宏观"},
                ))
        except Exception:
            pass

    except ImportError:
        pass

    return make_result("akshare_macro", items, time_filtered=False)
