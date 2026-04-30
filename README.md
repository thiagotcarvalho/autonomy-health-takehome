# autonomy-health-takehome

FHIR prior authorization review tool. A clinician-facing UI over bulk FHIR
data with deterministic eligibility logic and AI-assisted review.

Source spec: `docs/autonomy-health-assessment.md`.

## Project Structure

```
autonomy-health-takehome/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers (patients, patient_view, cohort)
│   │   ├── eligibility/      # Pure-function policy evaluator + cohort report
│   │   │   ├── evaluate.py   # Bariatric eligibility rules
│   │   │   ├── cohort.py     # Cohort-level aggregation
│   │   │   ├── store.py      # patient_summary row → dataclass
│   │   │   └── types.py      # Frozen dataclasses
│   │   ├── ingest/           # NDJSON → SQLite pipeline
│   │   │   ├── sources.py    # Shard discovery + streaming reader
│   │   │   ├── extract.py    # Field extractors (id, patient ref, date)
│   │   │   ├── loader.py     # Bulk INSERT into resources table
│   │   │   └── summary.py    # Derived patient_summary builder
│   │   ├── db.py             # SQLite connection + schema bootstrap
│   │   ├── main.py           # FastAPI app + lifespan
│   │   ├── models.py         # Pydantic response schemas
│   │   └── schema.sql        # Hybrid blob + summary tables
│   ├── benchmarks/
│   │   └── ingest_perf.md    # Profile-driven optimization writeup
│   ├── scripts/
│   │   └── ingest_cli.py     # Ingestion entry point
│   └── tests/                # pytest suite (64 tests)
├── frontend/
│   ├── src/
│   │   ├── components/ui/    # shadcn/ui primitives (button, card, …)
│   │   ├── lib/              # cn() utility, fetch client, types
│   │   ├── App.tsx           # Single-page app shell
│   │   ├── main.tsx
│   │   └── index.css         # Tailwind 4 import + theme
│   ├── index.html
│   ├── vite.config.ts        # /api proxy → :8000, @/ alias
│   ├── components.json       # shadcn config
│   └── package.json
├── data/
│   ├── fhir.db                                    # Built by `make ingest`
│   └── sample-bulk-fhir-datasets-1000-patients/   # Source NDJSON shards
├── docs/                     # Assessment brief
├── Makefile
└── pyproject.toml
```

The system has four layers:

1. **Ingest** reads bulk FHIR NDJSON shards into a hybrid SQLite store: a
   `resources` blob table preserves full JSON, and a derived `patient_summary`
   table holds the facts needed by the eligibility policy.
2. **Eligibility** is a pure function (`evaluate(summary)`) that applies the
   bariatric prior-authorization rules and returns a verdict plus per-check
   reasons and FHIR resource IDs as evidence. The same code path serves the
   per-patient API and the cohort report.
3. **API** (FastAPI) exposes `/api/patients`, `/api/patients/{id}`, and
   `/api/cohort/report`.
4. **Frontend** (React + Vite + Tailwind 4 + shadcn/ui) is a single-page app
   that talks to the API through a Vite dev proxy.

## Prerequisites

- Python 3.12+ for the backend
  - [uv](https://docs.astral.sh/uv/) for Python dependency management
- Node 22+ for the frontend
  - [npm](https://www.npmjs.com/) for TypeScript dependency management

## Backend

### Install dependencies

```bash
uv sync
```

### Build the SQLite database

The repository ships with the source FHIR NDJSON shards under
`data/sample-bulk-fhir-datasets-1000-patients/`. Ingest them:

```bash
make ingest
```

This produces `data/fhir.db` (~1.2 GB) containing 869,755 resources across
1,132 patients. The script wipes and rebuilds the DB on every run.

### Start the API server

```bash
make backend
```

Serves at `http://localhost:8000` with auto-reload. The server reads the DB
path from the `FHIR_DB_PATH` environment variable; by default it uses
`data/fhir.db`.

### Hit the endpoints

```bash
# List all patients (id + display_name)
curl http://localhost:8000/api/patients

# Per-patient view: snapshot, timeline, eligibility verdict
curl http://localhost:8000/api/patients/<patient_id>

# Cohort-level eligibility report
curl http://localhost:8000/api/cohort/report
```

Interactive docs are available at `http://localhost:8000/docs`.

### Inspecting the SQLite database

The DB has two tables: `resources` (raw FHIR JSON, indexed by `patient_id`,
`type`, and `effective_date`) and `patient_summary` (derived facts used by
the eligibility evaluator). The schema is defined in `backend/app/schema.sql`.

Open a SQLite shell:

```bash
sqlite3 data/fhir.db
```

Useful queries:

```sql
-- Row counts
SELECT COUNT(*) FROM resources;
SELECT COUNT(*) FROM patient_summary;

-- Resource breakdown by type
SELECT type, COUNT(*) FROM resources GROUP BY type;

-- Patients with a qualifying BMI
SELECT patient_id, latest_bmi
FROM patient_summary
WHERE latest_bmi >= 35
ORDER BY latest_bmi DESC
LIMIT 10;

-- Patients with both hypertension and a high BMI
SELECT patient_id, given_name, family_name, latest_bmi
FROM patient_summary
WHERE has_hypertension = 1 AND latest_bmi >= 40;

-- Inspect the raw FHIR JSON for one resource
SELECT json FROM resources WHERE id = '<resource_id>';
```

### Tests, lint, and format

```bash
make test     # 64 tests, runs in under half a second
make lint     # ruff check
make format   # ruff format
```

Tests use a tiny FHIR fixture under `backend/tests/fixtures/tiny/` (2 patients)
and never touch `data/fhir.db`.

### Resetting state

```bash
make clean       # removes data/fhir.db and any *.prof files
make ingest      # rebuilds the DB from source shards
```

## Frontend

The frontend is a Vite-powered single-page app under `frontend/`. It proxies
all `/api/*` requests to the backend at `http://localhost:8000`, so make sure
the backend is running first.

### Install dependencies

```bash
cd frontend && npm install
```

`make install` from the repo root does this alongside `uv sync`.

### Start the dev server

```bash
make frontend
```

Serves at `http://localhost:5173/` with hot module replacement. Keep `make
backend` running in another terminal so the proxied `/api/*` calls succeed.

### Production build (optional)

```bash
cd frontend && npm run build
```

Outputs static assets to `frontend/dist/`.
