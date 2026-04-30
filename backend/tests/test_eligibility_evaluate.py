from app.eligibility.evaluate import evaluate
from app.eligibility.types import PatientSummary


def _summary(**overrides) -> PatientSummary:
    defaults = {
        "patient_id": "test",
        "given_name": None,
        "family_name": None,
        "birth_date": None,
        "sex": None,
        "latest_bmi": None,
        "latest_bmi_date": None,
        "latest_bmi_evidence_id": None,
        "has_hypertension": None,
        "hypertension_evidence_id": None,
        "has_type2_diabetes": None,
        "type2_diabetes_evidence_id": None,
        "has_psych_eval": None,
        "psych_eval_evidence_id": None,
        "has_weight_loss_evidence": None,
        "weight_loss_evidence_id": None,
    }
    defaults.update(overrides)
    return PatientSummary(**defaults)


def _check_by_requirement(result, requirement):
    for check in result.checks:
        if check.requirement == requirement:
            return check
    raise AssertionError(f"missing check {requirement!r}")


class TestEvaluate:
    def test_bmi_over_40_with_all_docs_is_eligible(self):
        result = evaluate(
            _summary(
                latest_bmi=42.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "eligible"

    def test_bmi_36_with_hypertension_and_docs_is_eligible(self):
        result = evaluate(
            _summary(
                latest_bmi=36.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_hypertension=True,
                hypertension_evidence_id="Condition/htn-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "eligible"

    def test_bmi_36_with_t2d_and_docs_is_eligible(self):
        result = evaluate(
            _summary(
                latest_bmi=36.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_type2_diabetes=True,
                type2_diabetes_evidence_id="Condition/t2d-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "eligible"

    def test_bmi_below_35_is_not_eligible(self):
        result = evaluate(
            _summary(
                latest_bmi=30.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "not_eligible"
        bmi_check = _check_by_requirement(result, "BMI threshold")
        assert bmi_check.status == "not_met"
        assert "BMI" in bmi_check.reason or "bmi" in bmi_check.reason

    def test_missing_bmi_is_unknown_with_reason(self):
        result = evaluate(
            _summary(
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "unknown"
        bmi_check = _check_by_requirement(result, "BMI threshold")
        assert bmi_check.status == "unknown"
        assert "BMI" in bmi_check.reason or "bmi" in bmi_check.reason
        assert bmi_check.reason in result.unknown_reasons

    def test_bmi_36_with_unknown_comorbidity_is_unknown(self):
        result = evaluate(
            _summary(
                latest_bmi=36.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "unknown"
        comorbidity_check = _check_by_requirement(result, "Comorbidity present")
        assert comorbidity_check.status == "unknown"
        assert "comorbidity" in comorbidity_check.reason.lower()

    def test_bmi_42_no_psych_eval_is_unknown(self):
        result = evaluate(
            _summary(
                latest_bmi=42.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "unknown"
        psych_check = _check_by_requirement(result, "Psychological evaluation")
        assert psych_check.status == "unknown"
        assert "psychological" in psych_check.reason.lower()

    def test_bmi_42_no_weight_loss_evidence_is_unknown(self):
        result = evaluate(
            _summary(
                latest_bmi=42.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
            )
        )

        assert result.status == "unknown"
        weight_loss_check = _check_by_requirement(
            result, "Prior weight-loss attempts"
        )
        assert weight_loss_check.status == "unknown"
        assert "weight" in weight_loss_check.reason.lower()

    def test_eligibility_result_carries_evidence_ids_for_met_checks(self):
        result = evaluate(
            _summary(
                latest_bmi=36.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_hypertension=True,
                hypertension_evidence_id="Condition/htn-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )

        assert result.status == "eligible"
        bmi_check = _check_by_requirement(result, "BMI threshold")
        comorbidity_check = _check_by_requirement(result, "Comorbidity present")
        assert "Observation/bmi-1" in bmi_check.evidence
        assert "Condition/htn-1" in comorbidity_check.evidence

    def test_unknown_reasons_field_lists_each_unknown_check_reason(self):
        result = evaluate(_summary())

        unknown_check_reasons = [
            check.reason for check in result.checks if check.status == "unknown"
        ]
        assert result.unknown_reasons == unknown_check_reasons
        assert len(result.unknown_reasons) >= 1

    def test_checks_are_returned_in_stable_order(self):
        all_unknown = evaluate(_summary())
        all_met = evaluate(
            _summary(
                latest_bmi=42.0,
                latest_bmi_evidence_id="Observation/bmi-1",
                has_hypertension=True,
                hypertension_evidence_id="Condition/htn-1",
                has_psych_eval=True,
                psych_eval_evidence_id="Procedure/psych-1",
                has_weight_loss_evidence=True,
                weight_loss_evidence_id="DocumentReference/wl-1",
            )
        )
        below_threshold = evaluate(
            _summary(
                latest_bmi=20.0,
                latest_bmi_evidence_id="Observation/bmi-1",
            )
        )

        expected_order = [
            "BMI threshold",
            "Comorbidity present",
            "Psychological evaluation",
            "Prior weight-loss attempts",
        ]
        for result in (all_unknown, all_met, below_threshold):
            assert [
                check.requirement for check in result.checks
            ] == expected_order
