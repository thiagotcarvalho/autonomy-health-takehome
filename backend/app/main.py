"""FastAPI application entrypoint for the FHIR prior-authorization API.

Wires the lifespan hook (logging + startup warnings), the global
exception handler that sanitizes 500s without swallowing FastAPI's own
4xx flow, and the per-feature routers under `/api/*`.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .api import cohort as cohort_router
from .api import patients as patients_router

DB_PATH = Path(os.environ.get("FHIR_DB_PATH", "data/fhir.db"))

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configures logging and surfaces startup warnings.

    Args:
        app: The FastAPI instance whose `state` is populated.

    Yields:
        Control to FastAPI for the lifetime of the application.
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)
    startup_logger = logging.getLogger("app.startup")
    startup_logger.info(
        "startup: db_present=%s anthropic_key_present=%s",
        DB_PATH.exists(),
        bool(os.environ.get("ANTHROPIC_API_KEY")),
    )
    app.state.db_path = DB_PATH
    yield


app = FastAPI(
    title="FHIR Prior Authorization Review",
    lifespan=lifespan,
)

app.include_router(patients_router.router)
app.include_router(cohort_router.router)


@app.exception_handler(Exception)
async def handle_unhandled_exception(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Sanitizes unexpected errors to a generic 500 response.

    `HTTPException` is re-raised so FastAPI's built-in handler can keep
    producing the correct 4xx response with the caller-supplied detail.

    Args:
        _request: The incoming request (unused).
        exc: The exception raised by the route handler.

    Returns:
        A `JSONResponse` with HTTP 500 and a generic detail message.

    Raises:
        HTTPException: Re-raised when `exc` is itself an `HTTPException`
          so FastAPI's own handler can format the 4xx response.
    """
    if isinstance(exc, HTTPException):
        raise exc
    logging.getLogger("app.api").exception("unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )
