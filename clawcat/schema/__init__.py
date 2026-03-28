"""ClawCat Schema — Pydantic models defining all layer contracts."""

from clawcat.schema.brief import (
    Brief,
    BriefItem,
    BriefMetadata,
    BriefSection,
    ClawComment,
    TimeRange,
)
from clawcat.schema.item import FetchResult, Item
from clawcat.schema.task import SectionPlan, SourceSelection, TaskConfig
from clawcat.schema.user import UserProfile

__all__ = [
    "Brief",
    "BriefItem",
    "BriefMetadata",
    "BriefSection",
    "ClawComment",
    "FetchResult",
    "Item",
    "SectionPlan",
    "SourceSelection",
    "TaskConfig",
    "TimeRange",
    "UserProfile",
]
