.PHONY: install ingest backend frontend test clean

DATA_DIR ?= data/sample-bulk-fhir-datasets-1000-patients

install:
	uv sync --extra dev
	cd frontend && pnpm install

ingest:
	uv run python -m scripts.ingest_cli $(DATA_DIR)

backend:
	uv run uvicorn app.main:app --reload --port 8000 --app-dir backend

frontend:
	cd frontend && pnpm dev

test:
	uv run pytest -v

clean:
	rm -f data/fhir.db data/fhir.db-* *.prof
