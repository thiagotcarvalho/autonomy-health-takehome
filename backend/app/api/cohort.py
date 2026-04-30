"""Cohort eligibility report endpoint."""

from fastapi import APIRouter, Request

from ..db import connect
from ..eligibility.cohort import build_cohort_report
from ..models import CohortReport

router = APIRouter(prefix="/api/cohort", tags=["cohort"])


@router.get("/report", response_model=CohortReport)
def get_cohort_report(request: Request) -> CohortReport:
    """Returns the aggregate eligibility breakdown across every patient.

    Args:
        request: Incoming request; carries `app.state.db_path`.

    Returns:
        A `CohortReport` with totals, per-status counts and percentages,
        and the most common reasons for `unknown` verdicts.
    """
    conn = connect(request.app.state.db_path)
    try:
        report_payload = build_cohort_report(conn)
    finally:
        conn.close()
    return CohortReport(**report_payload)
