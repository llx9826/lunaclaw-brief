"""ClawCat configuration — powered by pydantic-settings.

Loads from: environment variables > .env > config.yaml (descending priority).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Tuple, Type

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class BrandSettings(BaseModel):
    name: str = "ClawCat"
    full_name: str = "ClawCat Brief"
    tagline: str = "AI-Powered Report Engine"
    author: str = "by llx & Luna"


class LLMSettings(BaseModel):
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model: str = "kimi-k2.5"
    validator_model: str = ""
    api_key: str = ""
    timeout: int = 180
    max_retries: int = 2


class ProxySettings(BaseModel):
    enabled: bool = False
    http: str = ""
    https: str = ""


class EmailSettings(BaseModel):
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    sender_email: str = ""
    password: str = ""
    to_emails: list[str] = []


class Settings(BaseSettings):
    """Root settings — merges config.yaml, .env, and env vars."""

    model_config = SettingsConfigDict(
        yaml_file=["config.yaml", "config.local.yaml"],
        yaml_file_encoding="utf-8",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    brand: BrandSettings = Field(default_factory=BrandSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    email: EmailSettings = Field(default_factory=EmailSettings)

    output_dir: str = "output"
    data_dir: str = "data"
    template_dir: str = "clawcat/templates"
    static_dir: str = "clawcat/static"
    user_profile_path: str = "data/user_profile.json"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Priority: init > env > .env > yaml (lowest)."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — call this everywhere instead of constructing Settings."""
    return Settings()
