"""Cohort eligibility report endpoint."""

from fastapi import APIRouter

from ..db import DbConn
from ..eligibility.cohort import build_cohort_report
from ..models import CohortReport

router = APIRouter(prefix="/api/cohort", tags=["cohort"])


@router.get("/report", response_model=CohortReport)
def get_cohort_report(conn: DbConn) -> CohortReport:
    """Returns the aggregate eligibility breakdown across every patient.

    Args:
        conn: Per-request SQLite connection from `get_db`.

    Returns:
        A `CohortReport` with totals, per-status counts and percentages,
        and the most common reasons for `unknown` verdicts.
    """
    return CohortReport(**build_cohort_report(conn))
