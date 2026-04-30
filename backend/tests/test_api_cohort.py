"""Tests for the `GET /api/cohort/report` aggregate endpoint."""


class TestGetCohortReport:
    def test_returns_aggregate_shape_with_all_three_statuses(
        self, seeded_test_client
    ):
        response = seeded_test_client.get("/api/cohort/report")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert set(body["counts"].keys()) == {
            "eligible",
            "not_eligible",
            "unknown",
        }
        assert set(body["percentages"].keys()) == {
            "eligible",
            "not_eligible",
            "unknown",
        }
        assert isinstance(body["top_unknown_reasons"], list)

    def test_returns_zeros_for_empty_cohort(self, empty_test_client):
        response = empty_test_client.get("/api/cohort/report")
        assert response.status_code == 200
        body = response.json()
        assert body == {
            "total": 0,
            "counts": {"eligible": 0, "not_eligible": 0, "unknown": 0},
            "percentages": {
                "eligible": 0.0,
                "not_eligible": 0.0,
                "unknown": 0.0,
            },
            "top_unknown_reasons": [],
        }
