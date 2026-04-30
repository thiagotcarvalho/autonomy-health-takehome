"""Pure-function evaluator for the bariatric prior-authorization policy.

Takes a `PatientSummary` (the derived facts plus their FHIR evidence
IDs) and returns a deterministic `EligibilityResult`. The same code
path serves the per-patient API and the cohort report — the function
performs no I/O so it stays trivially testable.
"""

from .types import (
    CheckResult,
    EligibilityResult,
    PatientSummary,
)

_BMI_QUALIFYING_THRESHOLD = 35.0
_BMI_COMORBIDITY_BYPASS_THRESHOLD = 40.0

_BMI_REQUIREMENT = "BMI threshold"
_COMORBIDITY_REQUIREMENT = "Comorbidity present"
_PSYCH_EVAL_REQUIREMENT = "Psychological evaluation"
_WEIGHT_LOSS_REQUIREMENT = "Prior weight-loss attempts"


def evaluate(summary: PatientSummary) -> EligibilityResult:
    """Applies the policy rules to one patient summary.

    Each check is computed independently from the underlying facts and
    paired with the FHIR resource ID(s) that justify it. The combinator
    folds the four checks into a final `eligible` / `not_eligible` /
    `unknown` verdict per the spec.

    Args:
        summary: The derived facts for a single patient.

    Returns:
        The final `EligibilityResult` with checks in stable order and
        the reasons for any `unknown` checks pre-aggregated for the
        cohort report.
    """
    bmi_check = _evaluate_bmi_threshold(summary)
    comorbidity_check = _evaluate_comorbidity(summary)
    psych_eval_check = _evaluate_psych_eval(summary)
    weight_loss_check = _evaluate_weight_loss(summary)

    checks = [
        bmi_check,
        comorbidity_check,
        psych_eval_check,
        weight_loss_check,
    ]
    unknown_reasons = [
        check.reason for check in checks if check.status == "unknown"
    ]
    status = _combine(summary, checks)
    return EligibilityResult(
        status=status,
        checks=checks,
        unknown_reasons=unknown_reasons,
    )


def _evaluate_bmi_threshold(summary: PatientSummary) -> CheckResult:
    if summary.latest_bmi is None:
        return CheckResult(
            requirement=_BMI_REQUIREMENT,
            status="unknown",
            reason="No BMI observation recorded for this patient.",
            evidence=[],
        )
    evidence = _evidence_list(summary.latest_bmi_evidence_id)
    if summary.latest_bmi >= _BMI_QUALIFYING_THRESHOLD:
        return CheckResult(
            requirement=_BMI_REQUIREMENT,
            status="met",
            reason=(
                f"Latest BMI of {summary.latest_bmi} is at or above the "
                f"threshold of {_BMI_QUALIFYING_THRESHOLD}."
            ),
            evidence=evidence,
        )
    return CheckResult(
        requirement=_BMI_REQUIREMENT,
        status="not_met",
        reason=(
            f"Latest BMI of {summary.latest_bmi} is below the threshold "
            f"of {_BMI_QUALIFYING_THRESHOLD}."
        ),
        evidence=evidence,
    )


def _evaluate_comorbidity(summary: PatientSummary) -> CheckResult:
    evidence: list[str] = []
    if summary.has_hypertension and summary.hypertension_evidence_id:
        evidence.append(summary.hypertension_evidence_id)
    if summary.has_type2_diabetes and summary.type2_diabetes_evidence_id:
        evidence.append(summary.type2_diabetes_evidence_id)
    if evidence:
        return CheckResult(
            requirement=_COMORBIDITY_REQUIREMENT,
            status="met",
            reason=(
                "Qualifying comorbidity (hypertension or type 2 diabetes) "
                "found in the patient record."
            ),
            evidence=evidence,
        )
    return CheckResult(
        requirement=_COMORBIDITY_REQUIREMENT,
        status="unknown",
        reason=(
            "No qualifying comorbidity (hypertension or type 2 diabetes) "
            "found in the patient record."
        ),
        evidence=[],
    )


def _evaluate_psych_eval(summary: PatientSummary) -> CheckResult:
    evidence = _evidence_list(summary.psych_eval_evidence_id)
    if summary.has_psych_eval and summary.psych_eval_evidence_id:
        return CheckResult(
            requirement=_PSYCH_EVAL_REQUIREMENT,
            status="met",
            reason="Psychological evaluation documented for this patient.",
            evidence=evidence,
        )
    return CheckResult(
        requirement=_PSYCH_EVAL_REQUIREMENT,
        status="unknown",
        reason=(
            "No psychological evaluation documentation found for this patient."
        ),
        evidence=evidence,
    )


def _evaluate_weight_loss(summary: PatientSummary) -> CheckResult:
    evidence = _evidence_list(summary.weight_loss_evidence_id)
    if summary.has_weight_loss_evidence and summary.weight_loss_evidence_id:
        return CheckResult(
            requirement=_WEIGHT_LOSS_REQUIREMENT,
            status="met",
            reason=(
                "Prior weight-loss attempt documentation found for this "
                "patient."
            ),
            evidence=evidence,
        )
    return CheckResult(
        requirement=_WEIGHT_LOSS_REQUIREMENT,
        status="unknown",
        reason=(
            "No prior weight-loss attempt documentation found for this patient."
        ),
        evidence=evidence,
    )


def _combine(summary: PatientSummary, checks: list[CheckResult]) -> str:
    checks_by_requirement = {check.requirement: check for check in checks}
    bmi_status = checks_by_requirement[_BMI_REQUIREMENT].status
    comorbidity_status = checks_by_requirement[_COMORBIDITY_REQUIREMENT].status
    psych_eval_status = checks_by_requirement[_PSYCH_EVAL_REQUIREMENT].status
    weight_loss_status = checks_by_requirement[_WEIGHT_LOSS_REQUIREMENT].status

    if bmi_status == "not_met":
        return "not_eligible"

    bmi_clears_comorbidity = (
        summary.latest_bmi is not None
        and summary.latest_bmi >= _BMI_COMORBIDITY_BYPASS_THRESHOLD
    )
    comorbidity_satisfied = (
        comorbidity_status == "met" or bmi_clears_comorbidity
    )

    if (
        bmi_status == "met"
        and comorbidity_satisfied
        and psych_eval_status == "met"
        and weight_loss_status == "met"
    ):
        return "eligible"

    return "unknown"


def _evidence_list(evidence_id: str | None) -> list[str]:
    return [evidence_id] if evidence_id else []
