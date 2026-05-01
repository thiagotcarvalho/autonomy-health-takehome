.PHONY: install ingest backend frontend test lint format clean

ENV_FILE := $(if $(wildcard .env),--env-file .env,)

install:
	uv sync
	cd frontend && npm install

ingest:
	PYTHONPATH=backend uv run python -m scripts.ingest_cli

backend:
	uv run $(ENV_FILE) uvicorn app.main:app --reload --port 8000 --app-dir backend

frontend:
	cd frontend && npm run dev

test:
	uv run pytest -v

lint:
	uv run ruff check backend

format:
	uv run ruff format backend

clean:
	rm -f data/fhir.db data/fhir.db-* *.prof
