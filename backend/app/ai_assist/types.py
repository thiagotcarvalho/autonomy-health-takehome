"""Frozen dataclasses for AI Assist responses and reconciliation.

Intentionally distinct from `eligibility.types` even though field
shapes overlap. The AI's `met` is a model claim that may be wrong;
the deterministic layer's `met` is a guarantee. Conflating the two
types is exactly how "AI may explain or contextualize, but not change
outcomes" gets violated.
"""

from dataclasses import dataclass, field
from typing import Literal

from ..eligibility.types import EligibilityResult

AICheckStatus = Literal["met", "not_met", "unknown"]
AIVerdict = Literal["eligible", "not_eligible", "unknown"]


@dataclass(frozen=True)
class AICheck:
    requirement: str
    status: AICheckStatus
    reason: str
    evidence: list[str]


@dataclass(frozen=True)
class AIAssessment:
    status: AIVerdict
    reasoning: str
    checks: list[AICheck]


@dataclass(frozen=True)
class CheckDisagreement:
    requirement: str
    deterministic_status: AICheckStatus
    ai_status: AICheckStatus


@dataclass(frozen=True)
class Reconciliation:
    """Differences between the AI assessment and the deterministic verdict.

    Attributes:
        verdict_agrees: Whether the overall statuses match.
        deterministic_status: The authoritative verdict.
        ai_status: The AI's verdict, surfaced for transparency.
        check_disagreements: Per-check status mismatches.
        hallucinated_evidence: Resource references the AI cited that
          were not present in the data we sent it.
    """

    verdict_agrees: bool
    deterministic_status: AIVerdict
    ai_status: AIVerdict
    check_disagreements: list[CheckDisagreement] = field(default_factory=list)
    hallucinated_evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AIAssistResult:
    ai: AIAssessment
    deterministic: EligibilityResult
    reconciliation: Reconciliation
