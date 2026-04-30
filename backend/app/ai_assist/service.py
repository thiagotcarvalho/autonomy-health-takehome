"""Orchestrator: build patient context, call the model, reconcile, return.

The single entry point the API endpoint calls. Keeps every other
module in this package free of cross-concern coupling — `client.py`
talks only to Anthropic, `reconcile.py` is a pure function, and the
schema/prompt modules are just data.
"""

import sqlite3
from typing import Any

import orjson

from ..eligibility.evaluate import evaluate
from ..eligibility.store import load_summary
from ..eligibility.types import PatientSummary
from ..util import compute_age
from .client import call_with_tool
from .prompt import SYSTEM_PROMPT, build_user_message
from .reconcile import reconcile
from .tool_schema import ASSESSMENT_TOOL
from .types import AIAssessment, AIAssistResult, AICheck

_RECENT_TIMELINE_LIMIT = 30


class PatientNotFound(Exception):
    """Raised when no `patient_summary` row exists for the given ID."""


def _build_eligibility_facts(summary: PatientSummary) -> dict[str, Any]:
    return {
        "latest_bmi": summary.latest_bmi,
        "latest_bmi_evidence_id": summary.latest_bmi_evidence_id,
        "has_hypertension": bool(summary.has_hypertension)
        if summary.has_hypertension is not None
        else None,
        "hypertension_evidence_id": summary.hypertension_evidence_id,
        "has_type2_diabetes": bool(summary.has_type2_diabetes)
        if summary.has_type2_diabetes is not None
        else None,
        "type2_diabetes_evidence_id": summary.type2_diabetes_evidence_id,
        "has_psych_eval": bool(summary.has_psych_eval)
        if summary.has_psych_eval is not None
        else None,
        "psych_eval_evidence_id": summary.psych_eval_evidence_id,
        "has_weight_loss_evidence": bool(summary.has_weight_loss_evidence)
        if summary.has_weight_loss_evidence is not None
        else None,
        "weight_loss_evidence_id": summary.weight_loss_evidence_id,
    }


_SEARCH_NOTES = (
    "Hypertension was searched via SNOMED 59621000. "
    "Type 2 diabetes via SNOMED 44054006. "
    "Psychological evaluation via Procedure SNOMED 408919008 (Psychosocial "
    "care) and 385892002 (Mental health screening). "
    "Prior weight-loss attempts: no codes searched — the dataset contains "
    "no weight-management interventions per audit (Procedures, "
    "ServiceRequests, DocumentReferences all checked)."
)


def _load_evidence_resources(
    conn: sqlite3.Connection, summary: PatientSummary
) -> tuple[list[dict], set[str]]:
    """Loads the FHIR JSON of every evidence resource named in the summary."""
    candidate_ids = [
        summary.latest_bmi_evidence_id,
        summary.hypertension_evidence_id,
        summary.type2_diabetes_evidence_id,
        summary.psych_eval_evidence_id,
        summary.weight_loss_evidence_id,
    ]
    resources: list[dict] = []
    citable_ids: set[str] = set()
    for evidence_id in candidate_ids:
        if not evidence_id:
            continue
        row = conn.execute(
            "SELECT json FROM resources WHERE id = ?",
            (evidence_id,),
        ).fetchone()
        if row is not None:
            resources.append(orjson.loads(row["json"]))
            citable_ids.add(evidence_id)
    return resources, citable_ids


def _load_recent_timeline(
    conn: sqlite3.Connection, patient_id: str
) -> tuple[list[dict], set[str]]:
    """Loads the most recent N Observation/Procedure resources, condensed."""
    rows = conn.execute(
        "SELECT id, type, json, effective_date FROM resources "
        "WHERE patient_id = ? AND type IN ('Observation', 'Procedure') "
        "ORDER BY effective_date IS NULL, effective_date DESC, id DESC "
        "LIMIT ?",
        (patient_id, _RECENT_TIMELINE_LIMIT),
    ).fetchall()
    timeline: list[dict] = []
    citable_ids: set[str] = set()
    for row in rows:
        body = orjson.loads(row["json"])
        timeline.append(
            {
                "resource_id": row["id"],
                "type": row["type"],
                "effective_date": row["effective_date"],
                "code": body.get("code"),
            }
        )
        citable_ids.add(row["id"])
    return timeline, citable_ids


def _build_patient_context(
    conn: sqlite3.Connection, summary: PatientSummary
) -> tuple[dict[str, Any], set[str]]:
    """Produces the model's input context plus the set of citable IDs."""
    patient_reference = f"Patient/{summary.patient_id}"
    citable_ids: set[str] = {patient_reference}

    evidence_resources, evidence_ids = _load_evidence_resources(conn, summary)
    citable_ids |= evidence_ids

    recent_timeline, timeline_ids = _load_recent_timeline(
        conn, summary.patient_id
    )
    citable_ids |= timeline_ids

    context = {
        "patient": {
            "reference": patient_reference,
            "given_name": summary.given_name,
            "family_name": summary.family_name,
            "age": compute_age(summary.birth_date),
            "sex": summary.sex,
        },
        "eligibility_facts": _build_eligibility_facts(summary),
        "search_notes": _SEARCH_NOTES,
        "evidence_resources": evidence_resources,
        "recent_timeline": recent_timeline,
    }
    return context, citable_ids


def _parse_ai_assessment(tool_input: dict[str, Any]) -> AIAssessment:
    """Maps the model's tool-input dict to the `AIAssessment` dataclass."""
    return AIAssessment(
        status=tool_input["status"],
        reasoning=tool_input["reasoning"],
        checks=[
            AICheck(
                requirement=check["requirement"],
                status=check["status"],
                reason=check["reason"],
                evidence=list(check["evidence"]),
            )
            for check in tool_input["checks"]
        ],
    )


def assist(conn: sqlite3.Connection, patient_id: str) -> AIAssistResult:
    """Runs the full AI Assist pipeline for one patient.

    Args:
        conn: Open SQLite connection scoped to the request.
        patient_id: Bare FHIR Patient `id`.

    Returns:
        An `AIAssistResult` with the AI assessment, deterministic
        verdict, and reconciliation between them.

    Raises:
        PatientNotFound: When no `patient_summary` row exists for
          `patient_id`.
        AIAssistNotConfigured: When `ANTHROPIC_API_KEY` is missing.
        AIAssistCallFailed: When the model API call fails or returns
          no tool-use block.
    """
    summary = load_summary(conn, patient_id)
    if summary is None:
        raise PatientNotFound(patient_id)

    deterministic = evaluate(summary)
    context, citable_ids = _build_patient_context(conn, summary)
    user_message = build_user_message(context)

    tool_input = call_with_tool(SYSTEM_PROMPT, user_message, ASSESSMENT_TOOL)
    ai_assessment = _parse_ai_assessment(tool_input)
    reconciliation = reconcile(deterministic, ai_assessment, citable_ids)

    return AIAssistResult(
        ai=ai_assessment,
        deterministic=deterministic,
        reconciliation=reconciliation,
    )
