.PHONY: install ingest backend frontend test lint format clean

DATA_DIR ?= data/sample-bulk-fhir-datasets-1000-patients

install:
	uv sync
	cd frontend && npm install

ingest:
	PYTHONPATH=backend uv run python -m scripts.ingest_cli $(DATA_DIR)

backend:
	uv run uvicorn app.main:app --reload --port 8000 --app-dir backend

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
