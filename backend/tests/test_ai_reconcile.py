"""Tests for the AI Assist reconciliation pure function.

The reconciliation step is the load-bearing safety net between the
model output and the deterministic verdict, so its three diff classes
each get a focused case: overall verdict, per-check status,
hallucinated evidence.
"""

from app.ai_assist.reconcile import reconcile
from app.ai_assist.types import AIAssessment, AICheck
from app.eligibility.evaluate import (
    BMI_REQUIREMENT,
    COMORBIDITY_REQUIREMENT,
    PSYCH_EVAL_REQUIREMENT,
    WEIGHT_LOSS_REQUIREMENT,
)
from app.eligibility.types import CheckResult, EligibilityResult


def _deterministic_unknown() -> EligibilityResult:
    return EligibilityResult(
        status="unknown",
        checks=[
            CheckResult(
                requirement=BMI_REQUIREMENT,
                status="met",
                reason="...",
                evidence=["Observation/bmi-1"],
            ),
            CheckResult(
                requirement=COMORBIDITY_REQUIREMENT,
                status="met",
                reason="...",
                evidence=["Condition/htn-1"],
            ),
            CheckResult(
                requirement=PSYCH_EVAL_REQUIREMENT,
                status="unknown",
                reason="...",
                evidence=[],
            ),
            CheckResult(
                requirement=WEIGHT_LOSS_REQUIREMENT,
                status="unknown",
                reason="...",
                evidence=[],
            ),
        ],
        unknown_reasons=[],
    )


def _ai_matching(deterministic: EligibilityResult) -> AIAssessment:
    return AIAssessment(
        status=deterministic.status,
        reasoning="Matches deterministic.",
        checks=[
            AICheck(
                requirement=check.requirement,
                status=check.status,
                reason=check.reason,
                evidence=list(check.evidence),
            )
            for check in deterministic.checks
        ],
    )


class TestReconcile:
    def test_clean_agreement_produces_empty_diffs(self):
        deterministic = _deterministic_unknown()
        ai = _ai_matching(deterministic)
        available_ids = {"Observation/bmi-1", "Condition/htn-1"}

        result = reconcile(deterministic, ai, available_ids)

        assert result.verdict_agrees is True
        assert result.deterministic_status == "unknown"
        assert result.ai_status == "unknown"
        assert result.check_disagreements == []
        assert result.hallucinated_evidence == []

    def test_overall_verdict_mismatch_flips_verdict_agrees(self):
        deterministic = _deterministic_unknown()
        ai = _ai_matching(deterministic)
        confident_ai = AIAssessment(
            status="eligible",
            reasoning="Model overconfident.",
            checks=ai.checks,
        )
        available_ids = {"Observation/bmi-1", "Condition/htn-1"}

        result = reconcile(deterministic, confident_ai, available_ids)

        assert result.verdict_agrees is False
        assert result.deterministic_status == "unknown"
        assert result.ai_status == "eligible"

    def test_per_check_status_mismatch_is_recorded(self):
        deterministic = _deterministic_unknown()
        # AI claims psych eval is met when deterministic says unknown.
        ai_checks = [
            AICheck(
                requirement=check.requirement,
                status="met"
                if check.requirement == PSYCH_EVAL_REQUIREMENT
                else check.status,
                reason=check.reason,
                evidence=["Procedure/psych-fake"]
                if check.requirement == PSYCH_EVAL_REQUIREMENT
                else list(check.evidence),
            )
            for check in deterministic.checks
        ]
        ai = AIAssessment(
            status=deterministic.status,
            reasoning="Disagrees on psych eval.",
            checks=ai_checks,
        )
        available_ids = {
            "Observation/bmi-1",
            "Condition/htn-1",
            "Procedure/psych-fake",
        }

        result = reconcile(deterministic, ai, available_ids)

        assert len(result.check_disagreements) == 1
        disagreement = result.check_disagreements[0]
        assert disagreement.requirement == PSYCH_EVAL_REQUIREMENT
        assert disagreement.deterministic_status == "unknown"
        assert disagreement.ai_status == "met"

    def test_evidence_outside_context_flagged_as_hallucinated(self):
        deterministic = _deterministic_unknown()
        # AI cites IDs that were not in the prompt context.
        ai = AIAssessment(
            status=deterministic.status,
            reasoning="Hallucinating sources.",
            checks=[
                AICheck(
                    requirement=BMI_REQUIREMENT,
                    status="met",
                    reason="...",
                    evidence=["Observation/bmi-1", "Observation/fake-bmi"],
                ),
                AICheck(
                    requirement=COMORBIDITY_REQUIREMENT,
                    status="met",
                    reason="...",
                    evidence=["Condition/never-existed"],
                ),
                AICheck(
                    requirement=PSYCH_EVAL_REQUIREMENT,
                    status="unknown",
                    reason="...",
                    evidence=[],
                ),
                AICheck(
                    requirement=WEIGHT_LOSS_REQUIREMENT,
                    status="unknown",
                    reason="...",
                    evidence=[],
                ),
            ],
        )
        available_ids = {"Observation/bmi-1", "Condition/htn-1"}

        result = reconcile(deterministic, ai, available_ids)

        assert result.hallucinated_evidence == [
            "Condition/never-existed",
            "Observation/fake-bmi",
        ]
        # Legitimate IDs are not flagged.
        assert "Observation/bmi-1" not in result.hallucinated_evidence
