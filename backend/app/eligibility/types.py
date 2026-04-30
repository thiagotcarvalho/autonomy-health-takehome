"""Pure data types shared by the eligibility evaluator and cohort report.

These dataclasses carry the information the policy logic operates on
and the verdict it returns. No DB or HTTP concerns leak in here so the
evaluator can be tested as a pure function.
"""

from dataclasses import dataclass
from typing import Literal

CheckStatus = Literal["met", "not_met", "unknown"]
EligibilityStatus = Literal["eligible", "not_eligible", "unknown"]


@dataclass(frozen=True)
class PatientSummary:
    """Mirror of a single row in the `patient_summary` SQLite table.

    Every derived fact is paired with the FHIR resource ID that justifies
    it (the `*_evidence_id` fields). Bool-shaped flags use three-valued
    logic: `True` for explicit presence, `None` for unknown. We never
    write `False`, so absence of evidence is always rendered as
    `unknown` downstream — matching the take-home's "missing data must
    be explicit" rule.

    Attributes:
        patient_id: FHIR Patient `id` (the bare id, not `Patient/<id>`).
        given_name: First given name from the Patient resource.
        family_name: Family name from the Patient resource.
        birth_date: ISO-8601 date string, or `None` if not recorded.
        sex: FHIR `Patient.gender` value (`female`, `male`, `other`,
          `unknown`), or `None` if not recorded.
        latest_bmi: Most recent body-mass-index value, or `None`.
        latest_bmi_date: ISO-8601 timestamp of the BMI observation.
        latest_bmi_evidence_id: `Observation/<id>` for the BMI value.
        has_hypertension: `True` if a qualifying Condition was found,
          `None` if none was.
        hypertension_evidence_id: `Condition/<id>` for the match.
        has_type2_diabetes: Same shape as `has_hypertension`.
        type2_diabetes_evidence_id: `Condition/<id>` for the match.
        has_psych_eval: `True` if a qualifying Procedure was found.
        psych_eval_evidence_id: `Procedure/<id>` for the match.
        has_weight_loss_evidence: Reserved — currently always `None` in
          this dataset (no qualifying Procedure codes exist).
        weight_loss_evidence_id: Reserved — paired with the above.
    """

    patient_id: str
    given_name: str | None
    family_name: str | None
    birth_date: str | None
    sex: str | None
    latest_bmi: float | None
    latest_bmi_date: str | None
    latest_bmi_evidence_id: str | None
    has_hypertension: bool | None
    hypertension_evidence_id: str | None
    has_type2_diabetes: bool | None
    type2_diabetes_evidence_id: str | None
    has_psych_eval: bool | None
    psych_eval_evidence_id: str | None
    has_weight_loss_evidence: bool | None
    weight_loss_evidence_id: str | None


@dataclass(frozen=True)
class CheckResult:
    """One requirement's verdict in the eligibility checklist.

    Attributes:
        requirement: Human-readable name of the policy requirement,
          e.g. `BMI threshold`.
        status: Whether the requirement is met, not met, or unknown.
        reason: One-sentence explanation suitable for surfacing in the
          UI tooltip and for inclusion in the cohort report's
          "top reasons for unknown status" breakdown.
        evidence: FHIR resource IDs that justify the verdict. Empty
          when the status is `unknown`.
    """

    requirement: str
    status: CheckStatus
    reason: str
    evidence: list[str]


@dataclass(frozen=True)
class EligibilityResult:
    """Outcome of evaluating the policy against one patient.

    Attributes:
        status: The terminal verdict for the patient.
        checks: One entry per requirement, in stable order.
        unknown_reasons: Convenience: the `reason` of every check whose
          status resolved to `unknown`. Populated by the evaluator so
          the cohort report can aggregate without re-walking `checks`.
    """

    status: EligibilityStatus
    checks: list[CheckResult]
    unknown_reasons: list[str]
