"""SQLite connection helper and schema initializer for the FHIR app."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def open_connection(db_path: Path | str) -> sqlite3.Connection:
    """Opens a SQLite connection configured for this application.

    The connection uses `sqlite3.Row` as its row factory so callers can
    access columns by name, and enables foreign-key enforcement.
    `check_same_thread=False` lets FastAPI's threadpool hand the same
    connection between worker threads across the lifetime of a single
    request; safe because each request owns its own connection.

    Args:
        db_path: Filesystem path to the SQLite database file. The file is
          created on first connection if it does not exist.

    Returns:
        An open SQLite connection. The caller is responsible for closing it.
    """
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Applies `schema.sql` to the connection.

    The schema uses `CREATE ... IF NOT EXISTS` for every object, so this
    function is safe to call repeatedly against the same database.

    Args:
        conn: An open SQLite connection produced by `open_connection`.
    """
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Yields a SQLite connection scoped to a single request.

    FastAPI dependency that opens a fresh connection per request,
    yields it to the route handler, and closes it in `finally` on the
    way out. Centralizes the connection lifecycle so handlers can
    declare `conn: DbConn` and stay focused on their query logic.

    Args:
        request: Incoming request; carries `app.state.db_path` set by
          the FastAPI lifespan hook.

    Yields:
        An open SQLite connection. Closed automatically when the
        handler returns or raises.
    """
    conn = open_connection(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


# Alias for route handlers: `def handler(conn: DbConn) -> ...`.
DbConn = Annotated[sqlite3.Connection, Depends(get_db)]
