"""Loaders that map `patient_summary` rows to `PatientSummary` dataclasses.

The single point where SQLite's INTEGER 1/NULL representation is
translated to Python's `True` / `None` for the boolean-flag columns,
so the rest of the eligibility code never sees raw rows.
"""

import sqlite3
from collections.abc import Iterator

from .types import PatientSummary


def _int_flag_to_bool(stored_value: int | None) -> bool | None:
    if stored_value is None:
        return None
    return bool(stored_value)


def _row_to_patient_summary(row: sqlite3.Row) -> PatientSummary:
    return PatientSummary(
        patient_id=row["patient_id"],
        given_name=row["given_name"],
        family_name=row["family_name"],
        birth_date=row["birth_date"],
        sex=row["sex"],
        latest_bmi=row["latest_bmi"],
        latest_bmi_date=row["latest_bmi_date"],
        latest_bmi_evidence_id=row["latest_bmi_evidence_id"],
        has_hypertension=_int_flag_to_bool(row["has_hypertension"]),
        hypertension_evidence_id=row["hypertension_evidence_id"],
        has_type2_diabetes=_int_flag_to_bool(row["has_type2_diabetes"]),
        type2_diabetes_evidence_id=row["type2_diabetes_evidence_id"],
        has_psych_eval=_int_flag_to_bool(row["has_psych_eval"]),
        psych_eval_evidence_id=row["psych_eval_evidence_id"],
        has_weight_loss_evidence=_int_flag_to_bool(
            row["has_weight_loss_evidence"]
        ),
        weight_loss_evidence_id=row["weight_loss_evidence_id"],
    )


def load_summary(
    conn: sqlite3.Connection, patient_id: str
) -> PatientSummary | None:
    """Loads the summary for a single patient.

    Args:
        conn: Open SQLite connection with the schema applied.
        patient_id: Bare patient ID (no `Patient/` prefix).

    Returns:
        The `PatientSummary` for that patient, or `None` if no row
        exists.
    """
    row = conn.execute(
        "SELECT * FROM patient_summary WHERE patient_id = ?",
        (patient_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_patient_summary(row)


def load_all_summaries(
    conn: sqlite3.Connection,
) -> Iterator[PatientSummary]:
    """Yields every `patient_summary` row as a `PatientSummary`.

    Streams via a server-side cursor so memory stays flat even if the
    cohort grows; ordering is by `patient_id` so cohort aggregations
    are deterministic.

    Args:
        conn: Open SQLite connection with the schema applied.

    Yields:
        One `PatientSummary` per row, in `patient_id` order.
    """
    cursor = conn.execute("SELECT * FROM patient_summary ORDER BY patient_id")
    for row in cursor:
        yield _row_to_patient_summary(row)
