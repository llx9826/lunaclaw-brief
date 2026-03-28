"""Grounding protocol — defines the interface for all checkers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from clawcat.schema.item import Item


class GroundingIssue(BaseModel):
    """A single quality issue found by a grounding checker."""

    checker: str
    severity: str = "info"
    message: str
    span: str = ""


class GroundingResult(BaseModel):
    """Aggregated result from one or more grounding checkers."""

    passed: bool = True
    score: float = 1.0
    issues: list[GroundingIssue] = []

    def merge(self, other: "GroundingResult") -> "GroundingResult":
        return GroundingResult(
            passed=self.passed and other.passed,
            score=(self.score + other.score) / 2,
            issues=self.issues + other.issues,
        )


class GroundingChecker(ABC):
    """Abstract base for all grounding/hallucination checkers."""

    name: str = "base"

    @abstractmethod
    def check(self, text: str, items: list[Item]) -> GroundingResult:
        """Check generated text (JSON or plain) against source items."""
        ...
