"""UserProfile — persistent user preference storage."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class UserProfile(BaseModel):
    """Stores per-user preferences so they don't repeat instructions."""

    user_id: str = "default"
    default_focus: list[str] = []
    preferred_sources: list[str] = []
    source_overrides: dict = {}
    excluded_topics: list[str] = []
    tone_preference: str = "professional"

    @classmethod
    def load(cls, path: Path) -> "UserProfile":
        if path.exists():
            return cls.model_validate_json(path.read_text(encoding="utf-8"))
        return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
