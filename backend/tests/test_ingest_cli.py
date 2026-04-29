import sqlite3
import subprocess
import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "tiny"
BACKEND_DIR = Path(__file__).resolve().parents[1]


class TestIngestCli:
    def test_creates_database_and_summary_from_fixture(self, tmp_path: Path):
        db_path = tmp_path / "fhir.db"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.ingest_cli",
                str(FIXTURE_DIR),
                "--db",
                str(db_path),
            ],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Ingest report" in result.stdout
        assert "Patient" in result.stdout
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        resource_count = conn.execute(
            "SELECT COUNT(*) FROM resources"
        ).fetchone()[0]
        summary_count = conn.execute(
            "SELECT COUNT(*) FROM patient_summary"
        ).fetchone()[0]
        assert resource_count == 5
        assert summary_count == 2

    def test_replaces_existing_database_on_rerun(self, tmp_path: Path):
        db_path = tmp_path / "fhir.db"

        for _ in range(2):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.ingest_cli",
                    str(FIXTURE_DIR),
                    "--db",
                    str(db_path),
                ],
                cwd=BACKEND_DIR,
                capture_output=True,
                text=True,
                check=True,
            )

        conn = sqlite3.connect(db_path)
        resource_count = conn.execute(
            "SELECT COUNT(*) FROM resources"
        ).fetchone()[0]
        assert resource_count == 5

    def test_returns_non_zero_when_data_dir_missing(self, tmp_path: Path):
        bogus_dir = tmp_path / "does-not-exist"
        db_path = tmp_path / "fhir.db"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.ingest_cli",
                str(bogus_dir),
                "--db",
                str(db_path),
            ],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "is not a directory" in result.stderr
