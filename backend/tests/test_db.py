from pathlib import Path

from app.db import connect, init_schema


def test_init_schema_creates_tables(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r[0] for r in rows]
    assert "resources" in names
    assert "patient_summary" in names


def test_init_schema_creates_indexes(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND name LIKE 'idx_%' "
        "ORDER BY name"
    ).fetchall()
    names = [r[0] for r in rows]
    assert "idx_resources_patient_type" in names
    assert "idx_resources_patient_time" in names


def test_connect_uses_row_factory(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    init_schema(conn)
    conn.execute(
        "INSERT INTO resources (id, type, patient_id, effective_at, json) "
        "VALUES (?, ?, ?, ?, ?)",
        ("Patient/abc", "Patient", "abc", None, "{}"),
    )
    row = conn.execute("SELECT id, type FROM resources").fetchone()
    assert row["id"] == "Patient/abc"
    assert row["type"] == "Patient"


def test_init_schema_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    init_schema(conn)
    init_schema(conn)  # second call should not raise
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r[0] for r in rows]
    assert "resources" in names
    assert "patient_summary" in names
