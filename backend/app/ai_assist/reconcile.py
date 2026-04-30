"""Pure-function reconciliation between AI and deterministic verdicts."""

from ..eligibility.types import EligibilityResult
from .types import (
    AIAssessment,
    CheckDisagreement,
    Reconciliation,
)


def reconcile(
    deterministic: EligibilityResult,
    ai: AIAssessment,
    available_resource_ids: set[str],
) -> Reconciliation:
    """Compares the AI's assessment against the deterministic verdict.

    Surfaces three classes of difference so the UI can warn the
    reviewer when the AI's read diverges from the source of truth:

    1. Overall verdict mismatch (`verdict_agrees`).
    2. Per-check status mismatch (`check_disagreements`).
    3. Resource references the AI cited that don't exist in the data
       we sent (`hallucinated_evidence`).

    Args:
        deterministic: The authoritative `EligibilityResult` produced
          by the pure-function evaluator.
        ai: The model's structured assessment.
        available_resource_ids: Every FHIR resource reference that
          appeared in the patient context shown to the model. Cited
          IDs outside this set are flagged as hallucinations.

    Returns:
        A `Reconciliation` summarising the comparison.
    """
    deterministic_checks_by_requirement = {
        check.requirement: check for check in deterministic.checks
    }

    check_disagreements = []
    for ai_check in ai.checks:
        deterministic_check = deterministic_checks_by_requirement.get(
            ai_check.requirement
        )
        if (
            deterministic_check is not None
            and deterministic_check.status != ai_check.status
        ):
            check_disagreements.append(
                CheckDisagreement(
                    requirement=ai_check.requirement,
                    deterministic_status=deterministic_check.status,
                    ai_status=ai_check.status,
                )
            )

    cited_resource_ids = {
        evidence_id
        for ai_check in ai.checks
        for evidence_id in ai_check.evidence
    }
    hallucinated = sorted(cited_resource_ids - available_resource_ids)

    return Reconciliation(
        verdict_agrees=deterministic.status == ai.status,
        deterministic_status=deterministic.status,
        ai_status=ai.status,
        check_disagreements=check_disagreements,
        hallucinated_evidence=hallucinated,
    )
