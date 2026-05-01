# Ingest Performance Optimization

**Result: 45.47s → 26.28s wall-clock (1.73x) on the full 1132-patient
dataset.** Single change: stdlib `json` swapped for `orjson` at the
three sites the profile flagged.

## Method

1. Build the naive baseline (single-row inserts, stdlib `json`).
2. Profile the full dataset under `cProfile`.
3. Apply one targeted change against the dominant cost line.
4. Re-measure under identical conditions.

## Dataset

The `1000-patients` branch of
[smart-on-fhir/sample-bulk-fhir-datasets](https://github.com/smart-on-fhir/sample-bulk-fhir-datasets/tree/1000-patients),
unpacked to `data/dataset/sample-bulk-fhir-datasets-1000-patients/`.
Resource counts ingested into the four in-scope types:

| Resource type    | Records  |
| ---------------- | -------: |
| Patient          | 1,132    |
| Condition        | 40,019   |
| Observation      | 648,136  |
| Procedure        | 180,468  |
| **Total**        | **869,755** |

Plus 1,132 derived `patient_summary` rows.

## The Baseline

```
   ncalls   tottime   cumtime   filename:function
1,739,510    21.600    21.600   decoder.py:raw_decode
1,739,510     0.822    26.233   __init__.py:loads
        1     4.944    25.938   summary.py:_bucket_resources_by_patient_and_type
  870,890     6.624     6.624   {method 'execute' of 'sqlite3.Connection' objects}
  869,755     6.000     6.000   encoder.py:iterencode
```

`json.loads` runs **1,739,510 times**, exactly twice per resource: once
during NDJSON load, once when summary build re-parses the stored `json`
column. `decoder.raw_decode` alone is 39% of profile self-time. SQLite
`execute` is a distant second at 12%.

My pre-profile guess was that per-row inserts would dominate. They
don't. Parsing did.

## The Changes

| File                            | Change                                       |
| ------------------------------- | -------------------------------------------- |
| `backend/app/ingest/sources.py` | `json.loads` → `orjson.loads` |
| `backend/app/ingest/loader.py`  | `json.dumps(...)` → `orjson.dumps(...).decode("utf-8")` |
| `backend/app/ingest/summary.py` | `json.loads(row["json"])` → `orjson.loads(...)` |

`orjson.dumps` returns bytes; `.decode("utf-8")` keeps the SQLite TEXT
column writable. All tests stay green.

## Post-Optimization Results

| Metric                                    | Baseline | Optimized | Speedup |
| ----------------------------------------- | -------: | --------: | ------: |
| Wall-clock total                          |  45.47s  |   26.28s  | **1.73x** |
| Load phase                                |  20.14s  |   10.10s  | 1.99x |
| Summary phase                             |  25.33s  |   16.18s  | 1.57x |
| `loads` self-time                         |  21.60s  |    3.72s  | **5.8x** |
| `dumps` self-time                         |   6.00s  |    0.71s  | **8.5x** |

Optimized profile, top entries:

```
   ncalls   tottime   cumtime   filename:function
        1    13.684   16.777   summary.py:_bucket_resources_by_patient_and_type
  870,890     4.805    4.805   {method 'execute' of 'sqlite3.Connection' objects}
1,739,510     3.720    3.720   {orjson.loads}
  869,755     0.709    0.709   {orjson.dumps}
```

The dominant cost line (parsing) was the right thing to fix first
because it hit two pipeline phases. Both load and summary sped up.

## Follow-Up

`_bucket_resources_by_patient_and_type` is now the dominant cost at
13.68s self-time. It iterates the cursor, decodes 870k JSON blobs, and
builds 870k namedtuples. To attack it:

1. **Skip the second decode.** Extract derived facts during the first
   pass and write `patient_summary` directly from `loader.load_resources`,
   merging the load and summary phases.
2. **Stream-batch the cursor.** Smaller win, cheaper to land.

At 1132 patients, neither is worth the complexity. At 10x scale, do (1).

Other candidates rejected:

- **`executemany` batching.** Python's `sqlite3` already wraps DML in an
  implicit transaction, so the 870k inserts are already one transaction.
  `execute` is 12% of time; batching shaves maybe a third. Less leverage
  than `orjson`.
- **Multiprocessing across shards.** Adds real complexity, can't help
  summary build (reads from DB, not files), and parallelism on a
  single-writer SQLite is bounded.
- **`PRAGMA journal_mode=WAL` / `synchronous=NORMAL`.** Tiny effect when
  writes are already in one transaction.

## Reproducing

```bash
make clean
PYTHONPATH=backend uv run python -m cProfile \
  -o backend/benchmarks/optimized.prof \
  -m scripts.ingest_cli
```

> `baseline.prof` and `optimized.prof` are checked in alongside this
writeup so the evidence is reproducible without re-running ingest. The
numbers above are from a 2026-04-29 run on macOS 26 (Darwin 25.4).
Re-running on a
different machine produces different absolute times but the same
relative cost structure.

## Opening a `.prof` file

Three options, in order of usefulness:

**SnakeViz (interactive flamegraph in the browser):**

```bash
uv run snakeviz backend/benchmarks/baseline.prof
```

or

```bash
uv run snakeviz backend/benchmarks/optimized.prof
```

Opens a local web server, renders an icicle/sunburst view. Click any
function to drill in.

**`pstats` one-liner (top 15 by self-time):**

```bash
uv run python -c "import pstats; pstats.Stats('backend/benchmarks/baseline.prof').strip_dirs().sort_stats('tottime').print_stats(15)"
```

or

```bash
uv run python -c "import pstats; pstats.Stats('backend/benchmarks/optimized.prof').strip_dirs().sort_stats('tottime').print_stats(15)"
```

**`pstats` interactive REPL:**

```bash
uv run python -m pstats backend/benchmarks/baseline.prof
```

or

```bash
uv run python -m pstats backend/benchmarks/optimized.prof
```

Then at the prompt: `strip`, `sort tottime`, `stats 15`. `help` lists
every command.
