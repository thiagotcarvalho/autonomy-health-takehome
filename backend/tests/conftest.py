"""Shared test fixtures for the API surface tests.

Provides a helper that builds a temp SQLite DB seeded from the tiny
fixture directory and yields a `TestClient` bound to that DB. Setting
`FHIR_DB_PATH` before reloading `app.main` ensures the lifespan hook
picks up the temp path without touching the real `data/fhir.db`.
"""

from collections.abc import Iterator
from importlib import reload
from pathlib import Path

import pytest
from app.db import init_schema, open_connection
from app.ingest.loader import load_resources
from app.ingest.summary import build_patient_summary
from fastapi.testclient import TestClient

_TINY_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "tiny"
_INGEST_TYPES = ("Patient", "Condition", "Observation", "Procedure")


def _seed_database(database_path: Path) -> None:
    conn = open_connection(database_path)
    init_schema(conn)
    load_resources(conn, _TINY_FIXTURE_DIR, types=_INGEST_TYPES)
    build_patient_summary(conn)
    conn.close()


def _build_test_client(database_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("FHIR_DB_PATH", str(database_path))
    import app.main as main_module

    reload(main_module)
    return TestClient(main_module.app)


@pytest.fixture
def seeded_test_client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    """Yields a `TestClient` bound to a freshly seeded temp database."""
    database_path = tmp_path / "fhir.db"
    _seed_database(database_path)
    with _build_test_client(database_path, monkeypatch) as client:
        yield client


@pytest.fixture
def empty_test_client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    """Yields a `TestClient` bound to an empty (schema-only) database."""
    database_path = tmp_path / "fhir.db"
    conn = open_connection(database_path)
    init_schema(conn)
    conn.close()
    with _build_test_client(database_path, monkeypatch) as client:
        yield client
