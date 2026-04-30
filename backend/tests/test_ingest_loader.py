import sqlite3
from pathlib import Path

import orjson
from app.db import init_schema, open_connection
from app.ingest.loader import load_resources

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "tiny"


def _open_test_db(db_path: Path) -> sqlite3.Connection:
    conn = open_connection(db_path)
    init_schema(conn)
    return conn


class TestLoadResources:
    def test_populates_resources_table_from_tiny_fixture(self, tmp_path: Path):
        conn = _open_test_db(tmp_path / "test.db")

        report = load_resources(
            conn,
            FIXTURE_DIR,
            types=("Patient", "Condition", "Observation"),
        )

        assert report["counts"] == {
            "Patient": 2,
            "Condition": 1,
            "Observation": 1,
        }
        assert report["skipped_no_patient"] == 0
        assert report["duplicates"] == 0

        rows = conn.execute(
            "SELECT id, type, patient_id, effective_date "
            "FROM resources ORDER BY id"
        ).fetchall()
        rows_by_id = {row["id"]: row for row in rows}
        assert rows_by_id["Patient/p1"]["patient_id"] == "p1"
        assert rows_by_id["Condition/c1"]["patient_id"] == "p1"
        assert (
            rows_by_id["Observation/o1"]["effective_date"]
            == "2024-03-01T10:00:00Z"
        )

    def test_skips_resources_without_patient_reference(self, tmp_path: Path):
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        (source_dir / "Device.000.ndjson").write_text(
            '{"resourceType":"Device","id":"d1"}\n'
        )
        conn = _open_test_db(tmp_path / "test.db")

        report = load_resources(conn, source_dir, types=("Device",))

        assert report["counts"] == {"Device": 0}
        assert report["skipped_no_patient"] == 1

    def test_replaces_duplicate_resource_ids(self, tmp_path: Path):
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        (source_dir / "Patient.000.ndjson").write_text(
            '{"resourceType":"Patient","id":"p1","gender":"female"}\n'
            '{"resourceType":"Patient","id":"p1","gender":"male"}\n'
        )
        conn = _open_test_db(tmp_path / "test.db")

        report = load_resources(conn, source_dir, types=("Patient",))

        assert report["counts"]["Patient"] == 1
        assert report["duplicates"] == 1

    def test_persists_only_the_last_value_when_duplicate(self, tmp_path: Path):
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        (source_dir / "Patient.000.ndjson").write_text(
            '{"resourceType":"Patient","id":"p1","gender":"female"}\n'
            '{"resourceType":"Patient","id":"p1","gender":"male"}\n'
        )
        conn = _open_test_db(tmp_path / "test.db")

        load_resources(conn, source_dir, types=("Patient",))

        stored_json = conn.execute(
            "SELECT json FROM resources WHERE id = 'Patient/p1'"
        ).fetchone()["json"]
        assert orjson.loads(stored_json)["gender"] == "male"
