"""时间解析工具 — 统一处理 ISO8601 时间字符串到本地 naive datetime。"""

from __future__ import annotations

from datetime import datetime


def parse_naive(s: str) -> datetime:
    """将 ISO8601 字符串解析为本地 naive datetime（去掉时区信息）。

    LLM 返回的时间可能带时区（如 +08:00 或 Z），统一转为本地时间后去掉 tzinfo。
    """
    dt = datetime.fromisoformat(s.replace("Z", "+00:00") if s.endswith("Z") else s)
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.replace(tzinfo=None)
