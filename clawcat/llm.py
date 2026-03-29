"""Shared LLM client factory — creates instructor-patched OpenAI client."""

from __future__ import annotations

from functools import lru_cache

import instructor
from openai import OpenAI

from clawcat.config import get_settings


@lru_cache
def get_instructor_client():
    """Get a cached instructor-patched OpenAI client (singleton)."""
    settings = get_settings()
    raw = OpenAI(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
        timeout=settings.llm.timeout,
    )
    return instructor.from_openai(raw, mode=instructor.Mode.MD_JSON)


def get_model() -> str:
    return get_settings().llm.model


def get_validator_model() -> str:
    """Cheap/fast model for llm_validator checks. Falls back to main model."""
    s = get_settings().llm
    return s.validator_model or s.model


def get_max_retries() -> int:
    return get_settings().llm.max_retries
