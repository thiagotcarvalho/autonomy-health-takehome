import sqlite3
from pathlib import Path

from app.db import init_schema, open_connection
from app.eligibility.store import load_all_summaries, load_summary
from app.eligibility.types import PatientSummary
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
    conn = open_connection(tmp_path / "test.db")
    init_schema(conn)
    load_resources(conn, FIXTURE_DIR, types=TINY_RESOURCE_TYPES)
    build_patient_summary(conn)
    return conn


class TestLoadSummary:
    def test_returns_patient_summary_dataclass(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        summary = load_summary(conn, "p1")

        assert isinstance(summary, PatientSummary)
        assert summary.patient_id == "p1"
        assert summary.given_name == "Jane"
        assert summary.family_name == "Doe"
        assert summary.sex == "female"
        assert summary.birth_date == "1972-05-10"
        assert summary.latest_bmi == 42.1
        assert summary.latest_bmi_evidence_id == "Observation/o1"

    def test_converts_sqlite_int_flags_to_python_bool(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        summary = load_summary(conn, "p1")

        assert summary.has_hypertension is True
        assert summary.has_psych_eval is True

    def test_preserves_null_flags_as_none(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        summary = load_summary(conn, "p2")

        assert summary.latest_bmi is None
        assert summary.has_hypertension is None
        assert summary.has_type2_diabetes is None
        assert summary.has_psych_eval is None
        assert summary.has_weight_loss_evidence is None

    def test_returns_none_for_unknown_patient(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        assert load_summary(conn, "does-not-exist") is None


class TestLoadAllSummaries:
    def test_yields_every_summary_row_in_order(self, tmp_path: Path):
        conn = _seeded_connection(tmp_path)

        summaries = list(load_all_summaries(conn))

        patient_ids = sorted(s.patient_id for s in summaries)
        assert patient_ids == ["p1", "p2"]
        assert all(isinstance(s, PatientSummary) for s in summaries)

    def test_returns_empty_iterator_when_table_empty(self, tmp_path: Path):
        conn = open_connection(tmp_path / "empty.db")
        init_schema(conn)

        summaries = list(load_all_summaries(conn))

        assert summaries == []
