from app.ingest.extract import (
    get_effective_date,
    get_patient_id,
    get_resource_id,
)


def test_get_resource_id_combines_type_and_id():
    resource = {"resourceType": "Patient", "id": "abc"}
    assert get_resource_id(resource) == "Patient/abc"


class TestGetPatientId:
    def test_patient_resource_is_its_own_patient(self):
        resource = {"resourceType": "Patient", "id": "abc"}
        assert get_patient_id(resource) == "abc"

    def test_resolves_from_subject_reference(self):
        resource = {
            "resourceType": "Condition",
            "id": "c1",
            "subject": {"reference": "Patient/p1"},
        }
        assert get_patient_id(resource) == "p1"

    def test_resolves_from_patient_reference(self):
        resource = {
            "resourceType": "Coverage",
            "id": "cv1",
            "patient": {"reference": "Patient/p9"},
        }
        assert get_patient_id(resource) == "p9"

    def test_handles_urn_uuid_reference(self):
        resource = {
            "resourceType": "Condition",
            "id": "c1",
            "subject": {"reference": "urn:uuid:p1"},
        }
        assert get_patient_id(resource) == "p1"

    def test_returns_none_when_no_reference_field(self):
        assert get_patient_id({"resourceType": "Device", "id": "d1"}) is None

    def test_returns_none_when_subject_lacks_reference_value(self):
        resource = {
            "resourceType": "Condition",
            "id": "c1",
            "subject": {"display": "Some patient"},
        }
        assert get_patient_id(resource) is None


class TestGetEffectiveDate:
    def test_uses_effective_datetime(self):
        resource = {
            "resourceType": "Observation",
            "effectiveDateTime": "2024-03-01T10:00:00Z",
        }
        assert get_effective_date(resource) == "2024-03-01T10:00:00Z"

    def test_falls_back_to_effective_period_start(self):
        resource = {
            "resourceType": "Observation",
            "effectivePeriod": {"start": "2024-01-01"},
        }
        assert get_effective_date(resource) == "2024-01-01"

    def test_uses_performed_datetime_for_procedures(self):
        resource = {
            "resourceType": "Procedure",
            "performedDateTime": "2023-12-15",
        }
        assert get_effective_date(resource) == "2023-12-15"

    def test_uses_recorded_date_for_conditions(self):
        resource = {
            "resourceType": "Condition",
            "recordedDate": "2022-06-01",
        }
        assert get_effective_date(resource) == "2022-06-01"

    def test_returns_none_when_no_date_present(self):
        assert get_effective_date({"resourceType": "Observation"}) is None
