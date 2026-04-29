import sqlite3
from pathlib import Path

from app.db import connect, init_schema
from app.ingest.loader import load_resources
from app.ingest.summary import build_patient_summary

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "tiny"
TINY_RESOURCE_TYPES = (
    "Patient",
    "Condition",
    "Observation",
    "Procedure",
)


def _seeded_connection(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "test.db")
    init_schema(conn)
    load_resources(conn, FIXTURE_DIR, types=TINY_RESOURCE_TYPES)
    return conn


def _summary_row(conn: sqlite3.Connection, patient_id: str) -> sqlite3.Row:
    return conn.execute(
        "SELECT * FROM patient_summary WHERE patient_id = ?",
        (patient_id,),
    ).fetchone()


class TestBuildPatientSummary:
    def test_creates_one_summary_row_per_patient(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        rows_written = build_patient_summary(conn)

        assert rows_written == 2
        patient_ids = [
            row["patient_id"]
            for row in conn.execute(
                "SELECT patient_id FROM patient_summary ORDER BY patient_id"
            )
        ]
        assert patient_ids == ["p1", "p2"]

    def test_extracts_demographics(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        build_patient_summary(conn)

        p1 = _summary_row(conn, "p1")
        assert p1["given_name"] == "Jane"
        assert p1["family_name"] == "Doe"
        assert p1["sex"] == "female"
        assert p1["birth_date"] == "1972-05-10"

    def test_extracts_latest_bmi_with_evidence(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        build_patient_summary(conn)

        p1 = _summary_row(conn, "p1")
        assert p1["latest_bmi"] == 42.1
        assert p1["latest_bmi_evidence_id"] == "Observation/o1"
        assert p1["latest_bmi_date"] == "2024-03-01T10:00:00Z"

    def test_extracts_hypertension_with_evidence(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        build_patient_summary(conn)

        p1 = _summary_row(conn, "p1")
        assert p1["has_hypertension"] == 1
        assert p1["hypertension_evidence_id"] == "Condition/c1"

    def test_extracts_psych_eval_with_evidence(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        build_patient_summary(conn)

        p1 = _summary_row(conn, "p1")
        assert p1["has_psych_eval"] == 1
        assert p1["psych_eval_evidence_id"] == "Procedure/proc1"

    def test_weight_loss_evidence_is_universally_unknown(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        build_patient_summary(conn)

        for patient_id in ("p1", "p2"):
            row = _summary_row(conn, patient_id)
            assert row["has_weight_loss_evidence"] is None
            assert row["weight_loss_evidence_id"] is None

    def test_missing_data_columns_remain_null(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        build_patient_summary(conn)

        p2 = _summary_row(conn, "p2")
        assert p2["latest_bmi"] is None
        assert p2["latest_bmi_evidence_id"] is None
        assert p2["has_hypertension"] is None
        assert p2["has_type2_diabetes"] is None
        assert p2["has_psych_eval"] is None

    def test_re_running_replaces_previous_summary(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        build_patient_summary(conn)
        build_patient_summary(conn)

        total = conn.execute("SELECT COUNT(*) FROM patient_summary").fetchone()[
            0
        ]
        assert total == 2
