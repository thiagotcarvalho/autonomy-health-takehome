"""CLI entry point for FHIR NDJSON ingest.

Wipes the target SQLite database and rebuilds it from a directory of
FHIR bulk NDJSON shards. The pipeline runs in two phases:

    1. Load: stream the in-scope resource types (`Patient`,
       `Condition`, `Observation`, `Procedure`) from disk into the
       `resources` blob table. See `app.ingest.loader`.
    2. Summarize: derive one `patient_summary` row per patient with
       the facts the eligibility evaluator needs (latest BMI, comorbid
       flags, psych-eval evidence, etc.). See `app.ingest.summary`.

The database is wiped on every run so the script is idempotent: the
output is a function of the input shards, not of any prior state.

Usage:
    python -m scripts.ingest_cli [data_dir] [--db data/fhir.db]

Arguments:
    data_dir: Optional. Directory containing the FHIR NDJSON shards
      (one file per resource type, e.g. `Patient.000.ndjson`). When
      omitted, the script auto-discovers a single subdirectory inside
      `data/dataset/`. The convention works with any FHIR dataset from
      https://github.com/smart-on-fhir/sample-bulk-fhir-datasets.
      Errors if the parent is missing or contains anything other than
      exactly one directory.
    --db: Output SQLite database path. Defaults to `data/fhir.db`. The
      flag exists primarily so tests can redirect ingest into a
      `tmp_path` fixture without clobbering the production DB.

Exit codes:
    0: success.
    1: argument errors (e.g. `data_dir` is not a directory, or the
       auto-discovery convention isn't met).
    2: recoverable ingest failures: filesystem (`OSError`), SQLite
       (`sqlite3.Error`), or malformed NDJSON (`orjson.JSONDecodeError`).
       Programming bugs (e.g. `AttributeError`) are intentionally not
       caught and propagate with a full traceback.
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

import orjson
from app.db import init_schema, open_connection
from app.ingest.loader import load_resources
from app.ingest.summary import build_patient_summary

RESOURCE_TYPES = ("Patient", "Condition", "Observation", "Procedure")
DEFAULT_DATASET_PARENT = Path("data/dataset")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest FHIR bulk NDJSON into SQLite.",
    )
    parser.add_argument(
        "data_dir",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "Directory containing FHIR bulk *.ndjson shards. When "
            "omitted, auto-discovers a single subdirectory inside "
            "data/dataset/."
        ),
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/fhir.db"),
        help="SQLite database path (default: data/fhir.db).",
    )
    return parser.parse_args(argv)


def _discover_dataset_dir(parent: Path) -> Path:
    """Returns the single dataset directory inside `parent`.

    Raises:
        FileNotFoundError: When `parent` does not exist.
        ValueError: When `parent` contains zero or more than one
          subdirectory. The message names every directory found so the
          caller can decide which to keep.
    """
    if not parent.is_dir():
        raise FileNotFoundError(
            f"Dataset parent directory {parent} does not exist. "
            f"Place a single FHIR dataset directory inside it."
        )
    candidates = sorted(entry for entry in parent.iterdir() if entry.is_dir())
    if not candidates:
        raise ValueError(
            f"No dataset directory found in {parent}. Place a single "
            f"FHIR dataset directory there."
        )
    if len(candidates) > 1:
        names = ", ".join(candidate.name for candidate in candidates)
        raise ValueError(
            f"Multiple dataset directories found in {parent} ({names}). "
            f"Only one FHIR dataset can be loaded at a time. Keep one "
            f"and remove (or move) the others."
        )
    return candidates[0]


def _print_report(
    load_report: dict,
    summary_rows_written: int,
    load_elapsed: float,
    summary_elapsed: float,
) -> None:
    total_elapsed = load_elapsed + summary_elapsed
    print()
    print("=== Ingest report ===")
    for resource_type, count in load_report["counts"].items():
        print(f"  {resource_type:<22} {count:>6}")
    print(f"  skipped (no patient)   {load_report['skipped_no_patient']:>6}")
    print(f"  duplicates             {load_report['duplicates']:>6}")
    print(f"  patient_summary rows   {summary_rows_written:>6}")
    print(f"  load time              {load_elapsed:>6.2f}s")
    print(f"  summary time           {summary_elapsed:>6.2f}s")
    print(f"  total                  {total_elapsed:>6.2f}s")


def main(argv: list[str] | None = None) -> int:
    """Runs the ingest pipeline against a directory of FHIR NDJSON shards.

    Wipes any existing database file at `--db`, applies the schema,
    loads the in-scope resource types, builds `patient_summary`, and
    prints a formatted report with row counts and timings.

    Args:
        argv: Optional argument list; defaults to `sys.argv[1:]`.

    Returns:
        Exit code: 0 on success, 1 on argument errors, 2 on filesystem,
        SQLite, or malformed-NDJSON failures during ingest. See the
        module docstring for the full contract.
    """
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("ingest")

    if args.data_dir is None:
        try:
            args.data_dir = _discover_dataset_dir(DEFAULT_DATASET_PARENT)
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        logger.info("Auto-discovered dataset at %s", args.data_dir)
    elif not args.data_dir.is_dir():
        print(
            f"error: {args.data_dir} is not a directory",
            file=sys.stderr,
        )
        return 1

    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        logger.info("Removing existing database at %s", args.db)
    args.db.unlink(missing_ok=True)
    logger.info("Initializing fresh database at %s", args.db)
    conn = open_connection(args.db)
    init_schema(conn)

    try:
        logger.info("Loading resources from %s", args.data_dir)
        load_started = time.perf_counter()
        load_report = load_resources(conn, args.data_dir, types=RESOURCE_TYPES)
        load_elapsed = time.perf_counter() - load_started

        logger.info("Building patient summary")
        summary_started = time.perf_counter()
        summary_rows_written = build_patient_summary(conn)
        summary_elapsed = time.perf_counter() - summary_started
    except OSError:
        logger.exception("Ingest failed: filesystem error")
        return 2
    except sqlite3.Error:
        logger.exception("Ingest failed: database error")
        return 2
    except orjson.JSONDecodeError:
        logger.exception("Ingest failed: malformed NDJSON in source shards")
        return 2

    _print_report(
        load_report,
        summary_rows_written,
        load_elapsed,
        summary_elapsed,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
