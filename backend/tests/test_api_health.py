"""Smoke test for the `/health` liveness endpoint."""

from app.main import app
from fastapi.testclient import TestClient


def test_health_returns_ok_status():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
