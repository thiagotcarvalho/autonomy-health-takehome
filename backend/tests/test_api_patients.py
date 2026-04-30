"""Tests for the `GET /api/patients` selector endpoint."""


class TestListPatients:
    def test_lists_seeded_patients_with_display_names(self, seeded_test_client):
        response = seeded_test_client.get("/api/patients")
        assert response.status_code == 200
        body = response.json()
        ids_returned = sorted(entry["id"] for entry in body)
        assert ids_returned == ["p1", "p2"]
        names_by_id = {entry["id"]: entry["display_name"] for entry in body}
        assert names_by_id["p1"] == "Jane Doe"
        assert names_by_id["p2"] == "John Roe"

    def test_returns_empty_list_when_no_patients(self, empty_test_client):
        response = empty_test_client.get("/api/patients")
        assert response.status_code == 200
        assert response.json() == []
