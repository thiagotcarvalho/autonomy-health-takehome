"""Cohort-level eligibility report.

Streams every patient summary, runs the deterministic evaluator
against each, and aggregates the verdicts plus the most common
reasons for `unknown` outcomes. The aggregation lives in Python (not
SQL) so the policy logic stays in one place.
"""

import sqlite3
from collections import Counter

from .evaluate import evaluate
from .store import load_all_summaries


def _percentage(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total * 100, 1)


def build_cohort_report(
    conn: sqlite3.Connection, top_n_reasons: int = 5
) -> dict:
    """Aggregates eligibility verdicts across every known patient.

    Iterates `load_all_summaries`, calls `evaluate` on each summary,
    and tallies the resulting statuses and the per-check `unknown`
    reasons. Percentages are rounded to one decimal place; an empty
    cohort returns zeroed counts without dividing by zero.

    Args:
        conn: Open SQLite connection with `patient_summary` populated.
        top_n_reasons: Maximum number of `unknown` reasons to include
          in the `top_unknown_reasons` list, sorted by descending
          count.

    Returns:
        A JSON-serializable dict with `total`, per-status `counts` and
        `percentages`, and a `top_unknown_reasons` list of
        `{reason, count}` entries.
    """
    status_counts = Counter()
    reason_counts: Counter[str] = Counter()
    total_patients = 0

    for summary in load_all_summaries(conn):
        total_patients += 1
        result = evaluate(summary)
        status_counts[result.status] += 1
        reason_counts.update(result.unknown_reasons)

    counts = {
        "eligible": status_counts.get("eligible", 0),
        "not_eligible": status_counts.get("not_eligible", 0),
        "unknown": status_counts.get("unknown", 0),
    }
    percentages = {
        status: _percentage(count, total_patients)
        for status, count in counts.items()
    }
    top_unknown_reasons = [
        {"reason": reason, "count": count}
        for reason, count in reason_counts.most_common(top_n_reasons)
    ]

    return {
        "total": total_patients,
        "counts": counts,
        "percentages": percentages,
        "top_unknown_reasons": top_unknown_reasons,
    }
