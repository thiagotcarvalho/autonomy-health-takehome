"""SQLite connection helper and schema initializer for the FHIR app."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Opens a SQLite connection configured for this application.

    The connection uses `sqlite3.Row` as its row factory so callers can
    access columns by name, and enables foreign-key enforcement.

    Args:
        db_path: Filesystem path to the SQLite database file. The file is
          created on first connection if it does not exist.

    Returns:
        An open SQLite connection. The caller is responsible for closing it.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Applies `schema.sql` to the connection.

    The schema uses `CREATE ... IF NOT EXISTS` for every object, so this
    function is safe to call repeatedly against the same database.

    Args:
        conn: An open SQLite connection produced by `connect`.
    """
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
