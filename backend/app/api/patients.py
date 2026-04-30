"""Patient list endpoint that powers the UI selector."""

from fastapi import APIRouter, Request

from ..db import connect
from ..models import PatientListItem

router = APIRouter(prefix="/api/patients", tags=["patients"])


def _build_display_name(
    given_name: str | None,
    family_name: str | None,
    patient_id: str,
) -> str:
    """Composes a user-facing label that gracefully handles missing parts.

    Args:
        given_name: First given name from the Patient resource, or
          `None` if not recorded.
        family_name: Family name from the Patient resource, or `None`.
        patient_id: Bare FHIR Patient `id`, used as the last-resort
          fallback so the selector always has something to show.

    Returns:
        Either `"family given"`, whichever name part is present, or the
        patient ID when neither name is available.
    """
    if given_name and family_name:
        return f"{family_name} {given_name}"
    if family_name:
        return family_name
    if given_name:
        return given_name
    return patient_id


@router.get("", response_model=list[PatientListItem])
def list_patients(request: Request) -> list[PatientListItem]:
    """Returns every known patient as a selector-friendly summary.

    Args:
        request: Incoming request; carries `app.state.db_path` set by
          the FastAPI lifespan hook.

    Returns:
        One `PatientListItem` per row in `patient_summary`, sorted by
        `family_name` then `given_name`.
    """
    conn = connect(request.app.state.db_path)
    try:
        rows = conn.execute(
            "SELECT patient_id, given_name, family_name "
            "FROM patient_summary "
            "ORDER BY family_name, given_name"
        ).fetchall()
    finally:
        conn.close()
    return [
        PatientListItem(
            id=row["patient_id"],
            display_name=_build_display_name(
                row["given_name"],
                row["family_name"],
                row["patient_id"],
            ),
        )
        for row in rows
    ]
