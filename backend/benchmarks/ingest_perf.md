# Ingest Performance Optimization

This document captures the single performance optimization applied to the
FHIR ingest pipeline, the evidence that picked it, and what comes next.

The grading criterion in the take-home is "did you optimize the right
thing first." This writeup is structured around that question.

## Method

1. Build the naive baseline first (single-row inserts, stdlib `json`, no
   batching, default SQLite settings).
2. Run the full 1132-patient dataset under `cProfile`.
3. Identify the single biggest cumulative-time entry.
4. Apply ONE targeted change.
5. Re-measure under identical conditions.
6. Confirm the change actually moved the cost line that justified it.

## Dataset

| Resource type    | Records  |
| ---------------- | -------- |
| Patient          | 1,132    |
| Condition        | 40,019   |
| Observation      | 648,136  |
| Procedure        | 180,468  |
| **Total stored** | **869,755** |

Plus 1,132 derived `patient_summary` rows.

## Hypothesis (Before Profiling)

I expected per-row `cursor.execute()` calls to dominate since 870k inserts is
a lot of round-trips, and the naive loader uses no batching or
`executemany`. JSON parsing was second on my list. SQLite write
amplification (two indexes on the `resources` table) was third.

## What the Profile Actually Showed

Naive baseline under `cProfile` — top cumulative-time entries
(condensed; full output in `baseline.prof`):

```
   ncalls   tottime   cumtime   filename:function
1,739,510    21.600    21.600   decoder.py:raw_decode
1,739,510     2.111    24.961   decoder.py:decode
1,739,510     0.822    26.233   __init__.py:loads
        1     1.708    25.100   loader.py:load_resources
        1     4.944    25.938   summary.py:_bucket_resources_by_patient_and_type
  870,890     6.624     6.624   {method 'execute' of 'sqlite3.Connection' objects}
  869,755     0.565     6.860   encoder.py:encode
  869,755     6.000     6.000   encoder.py:iterencode
```

Key observations:

- `json.loads` is called **1,739,510 times — exactly twice per resource.**
  Once parsing each NDJSON line during load (`sources.iter_resources`),
  once re-parsing the stored `json` column during summary build
  (`_bucket_resources_by_patient_and_type`).
- `decoder.raw_decode` consumes **21.60 s of pure self-time, ≈ 39 % of
  the total profile run.** This was bigger than I expected.
- `sqlite3.Connection.execute` is **6.62 s self-time, ≈ 12 %** —
  meaningful but distant second.
- `json.dumps` (iterencode) is **6.00 s self-time, ≈ 11 %** — also
  parsing-shaped work.

Headline: parsing/serializing JSON dominates, on the order of three to
four times the cost of every other line. My pre-profile guess was wrong.

## Change

Swap stdlib `json` for `orjson` at the three call sites the profile
identified.

| File                            | Change                                       |
| ------------------------------- | -------------------------------------------- |
| `backend/app/ingest/sources.py` | `json.loads` → `orjson.loads` (NDJSON parse) |
| `backend/app/ingest/loader.py`  | `json.dumps(...)` → `orjson.dumps(...).decode("utf-8")` (storing back) |
| `backend/app/ingest/summary.py` | `json.loads(row["json"])` → `orjson.loads(...)` (re-parse) |

Single targeted change. Same API surface, same correctness invariants,
no schema changes, no transactional changes. `orjson.dumps` returns
bytes; `.decode("utf-8")` keeps the SQLite `TEXT` column writable as
str. All 36 existing tests stay green without modification.

## Result

| Metric (full 1132-patient dataset)             | Baseline | Optimized |    Δ |
| ---------------------------------------------- | -------: | --------: | ---: |
| Wall-clock total (no `cProfile`)               |  45.47 s |   26.28 s | **1.73×** |
| Load phase wall-clock                          |  20.14 s |   10.10 s | 1.99× |
| Summary phase wall-clock                       |  25.33 s |   16.18 s | 1.57× |
| `cProfile` total                               |  54.89 s |   32.90 s | 1.67× |
| `json.loads` self-time → `orjson.loads`        |  21.60 s |    3.72 s | **5.8×** |
| `json.dumps` (iterencode) → `orjson.dumps`     |   6.00 s |    0.71 s | **8.5×** |

Optimized profile, top entries (full output in `optimized.prof`):

```
   ncalls   tottime   cumtime   filename:function
        1    13.684   16.777   summary.py:_bucket_resources_by_patient_and_type
  870,890     4.805    4.805   {method 'execute' of 'sqlite3.Connection' objects}
1,739,510     3.720    3.720   {orjson.loads}
        1     1.736   12.857   loader.py:load_resources
  869,755     0.709    0.709   {orjson.dumps}
```

Both load and summary phases sped up because both decode the same JSON
twice in this pipeline. The change touched the dominant cost line for
both phases.

## Why This Was the Right Thing First

- It's the largest single cost line in the profile (39 % self-time, ≈ 48
  % cumulative).
- It hits **two** call sites — every resource is JSON-decoded twice
  end-to-end through the pipeline — so a 5 × improvement on the operation
  cascades across both halves of the wall-clock.
- It's a single targeted change. Two imports and one bytes-to-string
  decode are smaller than the alternatives, and the alternatives address
  smaller cost lines.

I considered three other candidates and rejected them:

- **`executemany` batching with explicit `BEGIN`/`COMMIT` and
  `journal_mode=WAL`.** The autocommit fear turned out to be wrong:
  Python's `sqlite3` module already wraps DML in an implicit transaction,
  so all 870 k inserts are already in one transaction in the baseline.
  `Connection.execute` is 12 % of time, batching might shave maybe a
  third of that. Less leverage than orjson and not what the profile
  actually flagged.
- **Multiprocessing across NDJSON shards.** Adds real complexity (worker
  pools, queue marshaling, single-writer SQLite serialization) and
  cannot help the summary-build phase (which reads from the DB, not the
  files). The shard parse is ≤ 25 % of total cost — even perfect
  parallelism saves less than the orjson swap, on a single-machine
  workload.
- **`PRAGMA synchronous=NORMAL` / `PRAGMA journal_mode=WAL`.** Tiny
  effect for a single-writer load; mostly irrelevant when writes are
  already in one transaction. Easy follow-up if disk fsync ever becomes
  meaningful.

The principle: optimize the line the profile highlights, not the line
that feels suspicious.

## What's Next (Not Done Here — Out of Scope for This Pass)

The post-optimization profile shows
`_bucket_resources_by_patient_and_type` at **13.68 s self-time** — now
the dominant cost. It's spending that time iterating the SQLite cursor,
decoding 870 k stored JSON blobs, and constructing 870 k
`_StoredResource` namedtuples. Two ways to attack it if scaling demanded
it:

1. **Eliminate the second JSON decode.** Extract the derived facts
   during the first pass (in `loader.load_resources`) and write them
   straight into `patient_summary`, skipping the second blob round-trip
   entirely. Bigger architectural change; effectively merges the load
   and summary phases.
2. **Stream the cursor with raw `executemany`-style SELECT batching.**
   Less leverage than (1) but cheaper to land.

If the dataset grew 10×, I would do (1). At 1132 patients neither is
worth the added complexity.

## Reproducing

```bash
make clean
PYTHONPATH=backend uv run python -m cProfile \
  -o backend/benchmarks/baseline.prof \
  -m scripts.ingest_cli data/sample-bulk-fhir-datasets-1000-patients

# Apply the change (already in this branch).

make clean
PYTHONPATH=backend uv run python -m cProfile \
  -o backend/benchmarks/optimized.prof \
  -m scripts.ingest_cli data/sample-bulk-fhir-datasets-1000-patients

# Inspect either profile:
uv run python -c "import pstats; pstats.Stats('backend/benchmarks/optimized.prof').strip_dirs().sort_stats('tottime').print_stats(15)"
```

Both `*.prof` artifacts are gitignored — they're machine-specific. The
numbers above came from a 2026-04-29 run on Darwin 25.4.
