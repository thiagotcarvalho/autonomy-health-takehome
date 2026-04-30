"""Pydantic response models for the FHIR prior-authorization API.

These mirror the dataclasses in `app.eligibility.types` so the JSON
contract stays consistent with the pure-function eligibility layer.
The `CheckStatus` and `EligibilityStatus` literal aliases are
re-imported (rather than redeclared) so the shared types are the
single source of truth.
"""

from pydantic import BaseModel

from .eligibility.types import CheckStatus, EligibilityStatus


class CheckResultModel(BaseModel):
    """Mirror of `eligibility.types.CheckResult` for JSON responses."""

    requirement: str
    status: CheckStatus
    reason: str
    evidence: list[str]


class EligibilityResultModel(BaseModel):
    """Mirror of `eligibility.types.EligibilityResult` for JSON responses."""

    status: EligibilityStatus
    checks: list[CheckResultModel]
    unknown_reasons: list[str]


class PatientListItem(BaseModel):
    """Selector-friendly summary row for the patient list endpoint."""

    id: str
    display_name: str


class TimelineEntry(BaseModel):
    """One Observation or Procedure rendered on the patient timeline."""

    resource_id: str
    type: str
    display: str
    date: str | None


class ConditionEntry(BaseModel):
    """An active condition shown in the snapshot card."""

    resource_id: str
    display: str


class ProcedureEntry(BaseModel):
    """A recent procedure shown in the snapshot card."""

    resource_id: str
    display: str
    date: str | None


class ClinicalSnapshot(BaseModel):
    """Demographics and key clinical facts for one patient."""

    patient_id: str
    given_name: str | None
    family_name: str | None
    age: int | None
    sex: str | None
    latest_bmi: float | None
    latest_bmi_evidence_id: str | None
    active_conditions: list[ConditionEntry]
    recent_procedures: list[ProcedureEntry]


class PatientView(BaseModel):
    """Full per-patient response: snapshot, timeline, and eligibility."""

    snapshot: ClinicalSnapshot
    timeline: list[TimelineEntry]
    eligibility: EligibilityResultModel


class CohortReason(BaseModel):
    """One `(reason, count)` entry in the cohort report breakdown."""

    reason: str
    count: int


class CohortReport(BaseModel):
    """Aggregate cohort eligibility breakdown."""

    total: int
    counts: dict[str, int]
    percentages: dict[str, float]
    top_unknown_reasons: list[CohortReason]
