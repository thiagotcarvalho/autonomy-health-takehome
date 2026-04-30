import sqlite3
from pathlib import Path

from app.db import connect, init_schema
from app.eligibility.cohort import build_cohort_report


def _empty_db(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "cohort.db")
    init_schema(conn)
    return conn


_INSERT_SUMMARY_SQL = (
    "INSERT INTO patient_summary ("
    "patient_id, given_name, family_name, birth_date, sex, "
    "latest_bmi, latest_bmi_date, latest_bmi_evidence_id, "
    "has_hypertension, hypertension_evidence_id, "
    "has_type2_diabetes, type2_diabetes_evidence_id, "
    "has_psych_eval, psych_eval_evidence_id, "
    "has_weight_loss_evidence, weight_loss_evidence_id"
    ") VALUES ("
    "?, ?, ?, ?, ?, "
    "?, ?, ?, "
    "?, ?, "
    "?, ?, "
    "?, ?, "
    "?, ?"
    ")"
)


def _insert_summary(
    conn: sqlite3.Connection,
    patient_id: str,
    *,
    latest_bmi=None,
    latest_bmi_evidence_id=None,
    has_hypertension=None,
    hypertension_evidence_id=None,
    has_type2_diabetes=None,
    type2_diabetes_evidence_id=None,
    has_psych_eval=None,
    psych_eval_evidence_id=None,
    has_weight_loss_evidence=None,
    weight_loss_evidence_id=None,
) -> None:
    conn.execute(
        _INSERT_SUMMARY_SQL,
        (
            patient_id,
            None,
            None,
            None,
            None,
            latest_bmi,
            None,
            latest_bmi_evidence_id,
            has_hypertension,
            hypertension_evidence_id,
            has_type2_diabetes,
            type2_diabetes_evidence_id,
            has_psych_eval,
            psych_eval_evidence_id,
            has_weight_loss_evidence,
            weight_loss_evidence_id,
        ),
    )
    conn.commit()


class TestBuildCohortReport:
    def test_empty_db_returns_zero_counts_and_no_reasons(self, tmp_path: Path):
        conn = _empty_db(tmp_path)

        report = build_cohort_report(conn)

        assert report == {
            "total": 0,
            "counts": {"eligible": 0, "not_eligible": 0, "unknown": 0},
            "percentages": {
                "eligible": 0.0,
                "not_eligible": 0.0,
                "unknown": 0.0,
            },
            "top_unknown_reasons": [],
        }

    def test_aggregates_eligible_not_eligible_and_unknown_categories(
        self, tmp_path: Path
    ):
        conn = _empty_db(tmp_path)
        _insert_summary(
            conn,
            "eligible-1",
            latest_bmi=42.0,
            latest_bmi_evidence_id="Observation/bmi-elig",
            has_psych_eval=1,
            psych_eval_evidence_id="Procedure/psych-elig",
            has_weight_loss_evidence=1,
            weight_loss_evidence_id="DocumentReference/wl-elig",
        )
        _insert_summary(
            conn,
            "not-elig-1",
            latest_bmi=28.0,
            latest_bmi_evidence_id="Observation/bmi-low",
        )
        _insert_summary(conn, "unknown-1")
        _insert_summary(
            conn,
            "unknown-2",
            latest_bmi=36.0,
            latest_bmi_evidence_id="Observation/bmi-mid",
        )

        report = build_cohort_report(conn)

        assert report["total"] == 4
        assert report["counts"] == {
            "eligible": 1,
            "not_eligible": 1,
            "unknown": 2,
        }
        assert report["percentages"] == {
            "eligible": 25.0,
            "not_eligible": 25.0,
            "unknown": 50.0,
        }
        assert isinstance(report["top_unknown_reasons"], list)

    def test_top_unknown_reasons_orders_by_count_descending(
        self, tmp_path: Path
    ):
        conn = _empty_db(tmp_path)
        for index in range(3):
            _insert_summary(
                conn,
                f"missing-bmi-{index}",
                has_hypertension=1,
                hypertension_evidence_id=f"Condition/htn-{index}",
                has_psych_eval=1,
                psych_eval_evidence_id=f"Procedure/psych-{index}",
                has_weight_loss_evidence=1,
                weight_loss_evidence_id=f"DocumentReference/wl-{index}",
            )
        _insert_summary(
            conn,
            "missing-comorbidity",
            latest_bmi=36.0,
            latest_bmi_evidence_id="Observation/bmi-mid",
            has_psych_eval=1,
            psych_eval_evidence_id="Procedure/psych",
            has_weight_loss_evidence=1,
            weight_loss_evidence_id="DocumentReference/wl",
        )

        report = build_cohort_report(conn, top_n_reasons=5)

        top_reasons = report["top_unknown_reasons"]
        assert len(top_reasons) >= 2
        assert top_reasons[0]["count"] == 3
        assert "BMI" in top_reasons[0]["reason"]
        counts = [entry["count"] for entry in top_reasons]
        assert counts == sorted(counts, reverse=True)
