"""Naive baseline loader for FHIR NDJSON resources.

Walks each requested resource type, resolves the patient it belongs to,
and writes one row per resource into the `resources` table. Uses
single-row inserts and stdlib `json` deliberately so a follow-up
profile-driven pass can replace the dominant cost line.
"""

import json
import logging
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .extract import get_effective_date, get_patient_id, get_resource_id
from .sources import discover_shards, iter_resources

logger = logging.getLogger(__name__)

_INSERT_RESOURCE_SQL = (
    "INSERT OR REPLACE INTO resources "
    "(id, type, patient_id, effective_date, json) "
    "VALUES (?, ?, ?, ?, ?)"
)


def load_resources(
    conn: sqlite3.Connection,
    data_dir: Path,
    types: Iterable[str],
) -> dict:
    """Loads the requested FHIR resource types into the `resources` table.

    Resources lacking a resolvable patient reference are skipped and
    counted. Duplicate resource IDs are replaced in place via
    `INSERT OR REPLACE` and counted separately so the report distinguishes
    "we saw this twice" from "we couldn't link this".

    Args:
        conn: Open SQLite connection with the schema applied.
        data_dir: Directory containing FHIR NDJSON shards.
        types: Resource types to load, e.g. `("Patient", "Condition")`.

    Returns:
        A dict with:
          * `counts`: per-type number of distinct resources stored
          * `skipped_no_patient`: resources dropped for lack of a patient ref
          * `duplicates`: resources whose ID was already seen in this run
    """
    requested_types = tuple(types)
    shards = discover_shards(data_dir)
    counts: dict[str, int] = dict.fromkeys(requested_types, 0)
    skipped_no_patient = 0
    duplicates = 0
    seen_resource_ids: set[str] = set()

    for resource_type in requested_types:
        for resource in iter_resources(shards.get(resource_type, [])):
            resource_id = get_resource_id(resource)
            patient_id = get_patient_id(resource)
            if patient_id is None:
                skipped_no_patient += 1
                logger.warning("Skipping %s: no patient reference", resource_id)
                continue

            if resource_id in seen_resource_ids:
                duplicates += 1
            else:
                seen_resource_ids.add(resource_id)
                counts[resource_type] += 1

            conn.execute(
                _INSERT_RESOURCE_SQL,
                (
                    resource_id,
                    resource_type,
                    patient_id,
                    get_effective_date(resource),
                    json.dumps(resource),
                ),
            )

    conn.commit()
    return {
        "counts": counts,
        "skipped_no_patient": skipped_no_patient,
        "duplicates": duplicates,
    }
