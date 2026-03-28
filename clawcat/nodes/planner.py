"""Planner node — understands user intent, selects sources, designs report structure.

Reads registry.json + UserProfile, outputs TaskConfig via instructor.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from clawcat.config import get_settings
from clawcat.llm import get_instructor_client, get_model, get_max_retries
from clawcat.prompts.planner import PLANNER_SYSTEM
from clawcat.schema.task import TaskConfig
from clawcat.schema.user import UserProfile
from clawcat.state import PipelineState

logger = logging.getLogger(__name__)


def _load_registry() -> str:
    registry_path = Path("clawcat/adapters/registry.json")
    if registry_path.exists():
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        return json.dumps(data, ensure_ascii=False, indent=2)
    return "[]"


def _load_user_profile() -> UserProfile:
    settings = get_settings()
    return UserProfile.load(Path(settings.user_profile_path))


def planner_node(state: PipelineState) -> dict:
    """Planner: user_input → TaskConfig."""
    user_input = state.get("user_input", "")

    if not user_input:
        return {"error": "No user input provided"}

    registry = _load_registry()
    profile = _load_user_profile()
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        client = get_instructor_client()

        task_config = client.chat.completions.create(
            model=get_model(),
            response_model=TaskConfig,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM.format(
                    registry=registry,
                    user_profile=profile.model_dump_json(),
                    today=today,
                )},
                {"role": "user", "content": user_input},
            ],
            max_retries=get_max_retries(),
        )
    except Exception as e:
        logger.error("Planner LLM call failed: %s", e)
        return {"error": f"Planner failed: {e}"}

    now = datetime.now()
    if not task_config.since:
        if task_config.period == "daily":
            task_config.since = (now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        else:
            task_config.since = (now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
    if not task_config.until:
        task_config.until = now.isoformat()
    from clawcat.utils.time import parse_naive
    for attr in ("since", "until"):
        val = getattr(task_config, attr, "")
        if val and ("+" in val[10:] or val.endswith("Z")):
            setattr(task_config, attr, parse_naive(val).isoformat())

    logger.info(
        "Planner selected %d sources for topic=%s period=%s",
        len(task_config.selected_sources),
        task_config.topic,
        task_config.period,
    )

    return {"task_config": task_config}
