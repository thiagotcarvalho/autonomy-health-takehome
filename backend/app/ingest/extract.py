"""Field extractors for FHIR resources used during ingest.

Pulls the small set of facts the rest of the pipeline needs:
  * a canonical resource ID (`Type/id`) used as a SQLite primary key
  * the patient ID this resource belongs to
  * a single ISO-8601 timestamp for chronological ordering
"""

_PATIENT_REFERENCE_FIELDS = ("subject", "patient")
_DATE_FIELDS = (
    "effectiveDateTime",
    "performedDateTime",
    "recordedDate",
    "issued",
)
_PERIOD_FIELDS = ("effectivePeriod", "performedPeriod")


def get_resource_id(resource: dict) -> str:
    """Builds the canonical `Type/id` reference string for a resource.

    Args:
        resource: A parsed FHIR resource dict.

    Returns:
        The resource reference, e.g. `Patient/abc-123`.
    """
    return f"{resource['resourceType']}/{resource['id']}"


def get_patient_id(resource: dict) -> str | None:
    """Resolves the patient ID this resource belongs to.

    Patient resources reference themselves. Other resources resolve via
    `subject.reference` or `patient.reference`. The `Patient/` and
    `urn:uuid:` prefixes are stripped, leaving the bare ID.

    Args:
        resource: A parsed FHIR resource dict.

    Returns:
        The patient ID, or `None` if no patient reference can be found.
    """
    if resource.get("resourceType") == "Patient":
        return resource.get("id")
    for field in _PATIENT_REFERENCE_FIELDS:
        patient_reference = (resource.get(field) or {}).get("reference")
        if patient_reference:
            bare_id = patient_reference.rsplit("/", 1)[-1]
            return bare_id.rsplit(":", 1)[-1]
    return None


def get_effective_date(resource: dict) -> str | None:
    """Extracts a single ISO-8601 timestamp for timeline ordering.

    Tries the common scalar date fields first (`effectiveDateTime`,
    `performedDateTime`, `recordedDate`, `issued`), then falls back to
    the start of `effectivePeriod` or `performedPeriod`. Despite the
    name, the value may include a time component when the underlying
    FHIR field is a datetime.

    Args:
        resource: A parsed FHIR resource dict.

    Returns:
        An ISO-8601 timestamp string, or `None` if no date is recorded.
    """
    for field in _DATE_FIELDS:
        effective_date = resource.get(field)
        if effective_date:
            return effective_date
    for field in _PERIOD_FIELDS:
        period = resource.get(field) or {}
        period_start = period.get("start")
        if period_start:
            return period_start
    return None
