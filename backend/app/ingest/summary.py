"""Builds the `patient_summary` table from the contents of `resources`.

Reads back from `resources`, buckets resources per patient and resource
type, and writes one row per patient with the derived facts the
eligibility logic and AI grounding both depend on. Every derived fact
carries the source FHIR resource ID alongside it so downstream code can
cite the exact record.
"""

import logging
import sqlite3
from collections.abc import Iterable
from typing import NamedTuple

import orjson

logger = logging.getLogger(__name__)


_BMI_LOINC_CODE = "39156-5"

_HYPERTENSION_SNOMED_CODES = frozenset({"59621000"})
_TYPE2_DIABETES_SNOMED_CODES = frozenset({"44054006"})
_PSYCH_EVAL_PROCEDURE_CODES = frozenset({"408919008", "385892002"})

# The dataset does not represent weight-loss interventions, so this set
# is empty by design — every patient resolves as `unknown` on this axis.
# Defining the search space here keeps adding a code a one-line change.
_WEIGHT_LOSS_PROCEDURE_CODES: frozenset[str] = frozenset()


class _StoredResource(NamedTuple):
    resource_id: str
    body: dict
    effective_date: str | None


_INSERT_SUMMARY_SQL = (
    "INSERT INTO patient_summary ("
    "patient_id, given_name, family_name, birth_date, sex, "
    "latest_bmi, latest_bmi_date, latest_bmi_evidence_id, "
    "has_hypertension, hypertension_evidence_id, "
    "has_type2_diabetes, type2_diabetes_evidence_id, "
    "has_psych_eval, psych_eval_evidence_id, "
    "has_weight_loss_evidence, weight_loss_evidence_id"
    ") VALUES ("
    "?, ?, ?, ?, ?, "
    "?, ?, ?, "
    "?, ?, "
    "?, ?, "
    "?, ?, "
    "?, ?"
    ")"
)


def build_patient_summary(conn: sqlite3.Connection) -> int:
    """Populates `patient_summary` from the contents of `resources`.

    Wipes any existing summary rows first so this function is safe to
    re-run after a fresh ingest. Patients whose `Patient` resource is
    not present in the dataset are skipped — orphaned references should
    not surface as visible patients downstream.

    Args:
        conn: Open SQLite connection with the schema applied and
          `resources` already loaded.

    Returns:
        The number of `patient_summary` rows written.
    """
    conn.execute("DELETE FROM patient_summary")
    buckets = _bucket_resources_by_patient_and_type(conn)

    rows_written = 0
    for patient_id, resources_by_type in buckets.items():
        patient_records = resources_by_type.get("Patient")
        if not patient_records:
            continue
        demographics = _extract_demographics(patient_records[0].body)

        bmi_value, bmi_date, bmi_evidence_id = _find_latest_bmi(
            resources_by_type.get("Observation", [])
        )
        hypertension_evidence_id = _find_condition_with_codes(
            resources_by_type.get("Condition", []),
            _HYPERTENSION_SNOMED_CODES,
        )
        type2_diabetes_evidence_id = _find_condition_with_codes(
            resources_by_type.get("Condition", []),
            _TYPE2_DIABETES_SNOMED_CODES,
        )
        psych_eval_evidence_id = _find_procedure_with_codes(
            resources_by_type.get("Procedure", []),
            _PSYCH_EVAL_PROCEDURE_CODES,
        )
        weight_loss_evidence_id = _find_procedure_with_codes(
            resources_by_type.get("Procedure", []),
            _WEIGHT_LOSS_PROCEDURE_CODES,
        )

        conn.execute(
            _INSERT_SUMMARY_SQL,
            (
                patient_id,
                demographics["given_name"],
                demographics["family_name"],
                demographics["birth_date"],
                demographics["sex"],
                bmi_value,
                bmi_date,
                bmi_evidence_id,
                _presence_flag(hypertension_evidence_id),
                hypertension_evidence_id,
                _presence_flag(type2_diabetes_evidence_id),
                type2_diabetes_evidence_id,
                _presence_flag(psych_eval_evidence_id),
                psych_eval_evidence_id,
                _presence_flag(weight_loss_evidence_id),
                weight_loss_evidence_id,
            ),
        )
        rows_written += 1

    conn.commit()
    return rows_written


def _bucket_resources_by_patient_and_type(
    conn: sqlite3.Connection,
) -> dict[str, dict[str, list[_StoredResource]]]:
    buckets: dict[str, dict[str, list[_StoredResource]]] = {}
    cursor = conn.execute(
        "SELECT id, type, patient_id, effective_date, json "
        "FROM resources WHERE patient_id IS NOT NULL "
        "ORDER BY id"
    )
    for row in cursor:
        patient_bucket = buckets.setdefault(row["patient_id"], {})
        type_bucket = patient_bucket.setdefault(row["type"], [])
        type_bucket.append(
            _StoredResource(
                resource_id=row["id"],
                body=orjson.loads(row["json"]),
                effective_date=row["effective_date"],
            )
        )
    return buckets


def _extract_demographics(patient_record: dict) -> dict[str, str | None]:
    primary_name = (patient_record.get("name") or [{}])[0]
    given_names = primary_name.get("given") or [None]
    return {
        "given_name": given_names[0],
        "family_name": primary_name.get("family"),
        "birth_date": patient_record.get("birthDate"),
        "sex": patient_record.get("gender"),
    }


def _find_latest_bmi(
    observations: Iterable[_StoredResource],
) -> tuple[float | None, str | None, str | None]:
    candidates: list[tuple[str, str, float]] = []
    for observation in observations:
        codings = _get_codings(observation.body)
        if not any(c.get("code") == _BMI_LOINC_CODE for c in codings):
            continue
        bmi_value = (observation.body.get("valueQuantity") or {}).get("value")
        if bmi_value is None:
            continue
        candidates.append(
            (
                observation.effective_date or "",
                observation.resource_id,
                bmi_value,
            )
        )
    if not candidates:
        return None, None, None
    candidates.sort(key=lambda triple: (triple[0], triple[1]))
    latest_date, latest_id, latest_value = candidates[-1]
    return latest_value, (latest_date or None), latest_id


def _find_condition_with_codes(
    conditions: Iterable[_StoredResource],
    target_codes: frozenset[str],
) -> str | None:
    if not target_codes:
        return None
    for condition in conditions:
        codings = _get_codings(condition.body)
        if any(coding.get("code") in target_codes for coding in codings):
            return condition.resource_id
    return None


def _find_procedure_with_codes(
    procedures: Iterable[_StoredResource],
    target_codes: frozenset[str],
) -> str | None:
    if not target_codes:
        return None
    for procedure in procedures:
        codings = _get_codings(procedure.body)
        if any(coding.get("code") in target_codes for coding in codings):
            return procedure.resource_id
    return None


def _get_codings(resource_body: dict) -> list[dict]:
    return (resource_body.get("code") or {}).get("coding") or []


def _presence_flag(evidence_id: str | None) -> int | None:
    return None if evidence_id is None else 1
