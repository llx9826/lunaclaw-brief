"""Item schema — unified content item from any data source adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class Item(BaseModel):
    """Unified content item produced by every adapter.

    item_id is auto-computed from (title, source, url) if not provided.
    """

    title: str
    url: str = ""
    source: str
    raw_text: str = ""
    published_at: str | None = None
    meta: dict = {}
    item_id: str = ""
    is_supplementary: bool = False

    @model_validator(mode="after")
    def _ensure_item_id(self) -> "Item":
        if not self.item_id:
            normalized = f"{self.title.lower().strip()}|{self.source}|{self.url}"
            self.item_id = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return self

    @property
    def published_datetime(self) -> datetime | None:
        """Parse published_at into datetime, handling ISO8601 with timezones."""
        if not self.published_at:
            return None
        raw = self.published_at.strip()
        # Python 3.11+ fromisoformat handles most ISO8601 including Z and offsets
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone()  # convert to system local time
            return dt.replace(tzinfo=None)
        except (ValueError, TypeError):
            pass
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                     "%a, %d %b %Y %H:%M:%S %z",  # RSS pubDate
                     "%a, %d %b %Y %H:%M:%S GMT"):
            try:
                dt = datetime.strptime(raw, fmt)
                if dt.tzinfo is not None:
                    dt = dt.astimezone()
                return dt.replace(tzinfo=None)
            except (ValueError, IndexError):
                continue
        return None


class FetchResult(BaseModel):
    """Standardized output from every adapter's fetch() function."""

    source: str
    items: list[Item] = []
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    time_filtered: bool = False
