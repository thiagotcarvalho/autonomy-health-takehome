"""Tests for the per-patient `GET /api/patients/{id}` endpoint."""

import json
from importlib import reload
from pathlib import Path

from app.db import connect, init_schema
from fastapi.testclient import TestClient


class TestGetPatientView:
    def test_returns_full_view_for_existing_patient(self, seeded_test_client):
        response = seeded_test_client.get("/api/patients/p1")
        assert response.status_code == 200
        body = response.json()

        snapshot = body["snapshot"]
        assert snapshot["patient_id"] == "p1"
        assert snapshot["given_name"] == "Jane"
        assert snapshot["family_name"] == "Doe"
        assert snapshot["sex"] == "female"
        assert snapshot["latest_bmi"] == 42.1
        assert snapshot["latest_bmi_evidence_id"] == "Observation/o1"
        assert isinstance(snapshot["age"], int)

        assert any(
            entry["resource_id"] == "Observation/o1"
            for entry in body["timeline"]
        )

        assert body["eligibility"]["status"] in {
            "eligible",
            "not_eligible",
            "unknown",
        }

    def test_returns_404_for_unknown_patient(self, seeded_test_client):
        response = seeded_test_client.get("/api/patients/does-not-exist")
        assert response.status_code == 404
        assert response.json() == {"detail": "Patient does-not-exist not found"}

    def test_filters_inactive_conditions_from_active_conditions_list(
        self, tmp_path: Path, monkeypatch
    ):
        database_path = tmp_path / "fhir.db"
        _seed_two_conditions(database_path)
        monkeypatch.setenv("FHIR_DB_PATH", str(database_path))
        import app.main as main_module

        reload(main_module)
        with TestClient(main_module.app) as client:
            response = client.get("/api/patients/p1")

        assert response.status_code == 200
        active_ids = [
            entry["resource_id"]
            for entry in response.json()["snapshot"]["active_conditions"]
        ]
        assert "Condition/active-one" in active_ids
        assert "Condition/resolved-one" not in active_ids


def _seed_two_conditions(database_path: Path) -> None:
    """Seeds a minimal DB with one active and one resolved condition.

    Bypasses the loader so we can inject a `clinicalStatus.coding[0].code`
    of `resolved`, which the tiny fixture does not exercise.
    """
    conn = connect(database_path)
    init_schema(conn)
    conn.execute(
        "INSERT INTO patient_summary (patient_id, given_name, family_name) "
        "VALUES ('p1', 'Jane', 'Doe')"
    )
    active_condition_body = {
        "resourceType": "Condition",
        "id": "active-one",
        "subject": {"reference": "Patient/p1"},
        "code": {"text": "Active condition"},
        "clinicalStatus": {"coding": [{"code": "active"}]},
    }
    resolved_condition_body = {
        "resourceType": "Condition",
        "id": "resolved-one",
        "subject": {"reference": "Patient/p1"},
        "code": {"text": "Resolved condition"},
        "clinicalStatus": {"coding": [{"code": "resolved"}]},
    }
    insert_resource_sql = (
        "INSERT INTO resources "
        "(id, type, patient_id, effective_date, json) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    conn.execute(
        insert_resource_sql,
        (
            "Condition/active-one",
            "Condition",
            "p1",
            None,
            json.dumps(active_condition_body),
        ),
    )
    conn.execute(
        insert_resource_sql,
        (
            "Condition/resolved-one",
            "Condition",
            "p1",
            None,
            json.dumps(resolved_condition_body),
        ),
    )
    conn.commit()
    conn.close()
