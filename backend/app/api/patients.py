"""Patient endpoints: selector list and per-patient review payload.

The list endpoint powers the UI selector. The detail endpoint assembles
the three regions a clinician needs in one round-trip — snapshot
demographics, the chronological timeline, and the deterministic
eligibility verdict — so the frontend can render a full review without
a follow-up query.
"""

import sqlite3
from datetime import date

import orjson
from fastapi import APIRouter, HTTPException

from ..db import DbConn
from ..eligibility.evaluate import evaluate
from ..eligibility.store import load_summary
from ..eligibility.types import PatientSummary
from ..models import (
    CheckResultModel,
    ClinicalSnapshot,
    ConditionEntry,
    EligibilityResultModel,
    PatientListItem,
    PatientView,
    ProcedureEntry,
    TimelineEntry,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])

_RECENT_PROCEDURE_LIMIT = 10
_TIMELINE_RESOURCE_TYPES = ("Observation", "Procedure")


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
        Either `"given family"`, whichever name part is present, or the
        patient ID when neither name is available.
    """
    if given_name and family_name:
        return f"{given_name} {family_name}"
    if family_name:
        return family_name
    if given_name:
        return given_name
    return patient_id


def _is_active_condition(condition_body: dict) -> bool:
    clinical_status_codings = (condition_body.get("clinicalStatus") or {}).get(
        "coding"
    ) or []
    return any(
        coding.get("code") == "active" for coding in clinical_status_codings
    )


def _resolve_display(resource_body: dict) -> str:
    code_block = resource_body.get("code") or {}
    text_value = code_block.get("text")
    if text_value:
        return text_value
    codings = code_block.get("coding") or []
    if codings:
        first_coding = codings[0]
        return (
            first_coding.get("display")
            or first_coding.get("code")
            or "(unknown)"
        )
    return "(unknown)"


def _compute_age(birth_date: str | None) -> int | None:
    if not birth_date:
        return None
    try:
        parsed_birth_date = date.fromisoformat(birth_date)
    except ValueError:
        return None
    today = date.today()
    had_birthday = (today.month, today.day) >= (
        parsed_birth_date.month,
        parsed_birth_date.day,
    )
    return today.year - parsed_birth_date.year - (0 if had_birthday else 1)


def _query_active_conditions(
    conn: sqlite3.Connection, patient_id: str
) -> list[ConditionEntry]:
    rows = conn.execute(
        "SELECT id, json FROM resources "
        "WHERE patient_id = ? AND type = 'Condition' "
        "ORDER BY id",
        (patient_id,),
    ).fetchall()
    active_entries: list[ConditionEntry] = []
    for row in rows:
        condition_body = orjson.loads(row["json"])
        if not _is_active_condition(condition_body):
            continue
        active_entries.append(
            ConditionEntry(
                resource_id=row["id"],
                display=_resolve_display(condition_body),
            )
        )
    return active_entries


def _query_recent_procedures(
    conn: sqlite3.Connection, patient_id: str
) -> list[ProcedureEntry]:
    rows = conn.execute(
        "SELECT id, json, effective_date FROM resources "
        "WHERE patient_id = ? AND type = 'Procedure' "
        "ORDER BY effective_date IS NULL, effective_date DESC, id DESC "
        "LIMIT ?",
        (patient_id, _RECENT_PROCEDURE_LIMIT),
    ).fetchall()
    return [
        ProcedureEntry(
            resource_id=row["id"],
            display=_resolve_display(orjson.loads(row["json"])),
            date=row["effective_date"],
        )
        for row in rows
    ]


def _build_snapshot(
    conn: sqlite3.Connection, summary: PatientSummary
) -> ClinicalSnapshot:
    return ClinicalSnapshot(
        patient_id=summary.patient_id,
        given_name=summary.given_name,
        family_name=summary.family_name,
        age=_compute_age(summary.birth_date),
        sex=summary.sex,
        latest_bmi=summary.latest_bmi,
        latest_bmi_evidence_id=summary.latest_bmi_evidence_id,
        active_conditions=_query_active_conditions(conn, summary.patient_id),
        recent_procedures=_query_recent_procedures(conn, summary.patient_id),
    )


def _build_timeline(
    conn: sqlite3.Connection, patient_id: str
) -> list[TimelineEntry]:
    type_placeholders = ",".join("?" * len(_TIMELINE_RESOURCE_TYPES))
    rows = conn.execute(
        f"SELECT id, type, json, effective_date FROM resources "
        f"WHERE patient_id = ? AND type IN ({type_placeholders}) "
        f"ORDER BY effective_date IS NULL, effective_date ASC, id ASC",
        (patient_id, *_TIMELINE_RESOURCE_TYPES),
    ).fetchall()
    return [
        TimelineEntry(
            resource_id=row["id"],
            type=row["type"],
            display=_resolve_display(orjson.loads(row["json"])),
            date=row["effective_date"],
        )
        for row in rows
    ]


def _serialize_eligibility(
    summary: PatientSummary,
) -> EligibilityResultModel:
    eligibility_result = evaluate(summary)
    return EligibilityResultModel(
        status=eligibility_result.status,
        checks=[
            CheckResultModel(
                requirement=check.requirement,
                status=check.status,
                reason=check.reason,
                evidence=list(check.evidence),
            )
            for check in eligibility_result.checks
        ],
        unknown_reasons=list(eligibility_result.unknown_reasons),
    )


@router.get("", response_model=list[PatientListItem])
def list_patients(conn: DbConn) -> list[PatientListItem]:
    """Returns every known patient as a selector-friendly summary.

    Args:
        conn: Per-request SQLite connection from `get_db`.

    Returns:
        One `PatientListItem` per row in `patient_summary`, sorted by
        `family_name` then `given_name`.
    """
    rows = conn.execute(
        "SELECT patient_id, given_name, family_name "
        "FROM patient_summary "
        "ORDER BY family_name, given_name"
    ).fetchall()
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


@router.get("/{patient_id}", response_model=PatientView)
def get_patient_view(patient_id: str, conn: DbConn) -> PatientView:
    """Returns the full review payload for one patient.

    Args:
        patient_id: Bare FHIR Patient `id` (no `Patient/` prefix).
        conn: Per-request SQLite connection from `get_db`.

    Returns:
        A `PatientView` containing the snapshot, timeline, and
        deterministic eligibility verdict.

    Raises:
        HTTPException: 404 when no `patient_summary` row exists for
          `patient_id`.
    """
    summary = load_summary(conn, patient_id)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient {patient_id} not found",
        )
    return PatientView(
        snapshot=_build_snapshot(conn, summary),
        timeline=_build_timeline(conn, patient_id),
        eligibility=_serialize_eligibility(summary),
    )
