.PHONY: install ingest backend frontend test lint format clean

DATA_DIR ?= data/sample-bulk-fhir-datasets-1000-patients

install:
	uv sync
	cd frontend && pnpm install

ingest:
	uv run python -m scripts.ingest_cli $(DATA_DIR)

backend:
	uv run uvicorn app.main:app --reload --port 8000 --app-dir backend

frontend:
	cd frontend && pnpm dev

test:
	uv run pytest -v

lint:
	uv run ruff check backend

format:
	uv run ruff format backend

clean:
	rm -f data/fhir.db data/fhir.db-* *.prof
