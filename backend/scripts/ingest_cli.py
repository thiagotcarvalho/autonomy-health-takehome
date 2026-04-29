"""CLI entry point for FHIR NDJSON ingest.

Usage:
    python -m scripts.ingest_cli <data_dir> [--db data/fhir.db]
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from app.db import connect, init_schema
from app.ingest.loader import load_resources
from app.ingest.summary import build_patient_summary

RESOURCE_TYPES = ("Patient", "Condition", "Observation", "Procedure")


def main(argv: list[str] | None = None) -> int:
    """Runs the ingest pipeline against a directory of FHIR NDJSON shards.

    Wipes any existing database file at `--db`, applies the schema,
    loads the in-scope resource types, builds `patient_summary`, and
    prints a formatted report with row counts and timings.

    Args:
        argv: Optional argument list; defaults to `sys.argv[1:]`.

    Returns:
        Exit code: 0 on success, 1 on argument errors, 2 on
        unexpected ingest failures.
    """
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("ingest")

    if not args.data_dir.is_dir():
        print(
            f"error: {args.data_dir} is not a directory",
            file=sys.stderr,
        )
        return 1

    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.db.unlink(missing_ok=True)
    conn = connect(args.db)
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
    except Exception:
        logger.exception("Ingest failed")
        return 2

    _print_report(
        load_report,
        summary_rows_written,
        load_elapsed,
        summary_elapsed,
    )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest FHIR bulk NDJSON into SQLite.",
    )
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Directory containing FHIR bulk *.ndjson shards.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/fhir.db"),
        help="SQLite database path (default: data/fhir.db).",
    )
    return parser.parse_args(argv)


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


if __name__ == "__main__":
    sys.exit(main())
