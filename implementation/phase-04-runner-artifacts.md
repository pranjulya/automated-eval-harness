# Phase 04 — Evaluation Runner, Immutable Artifacts, Replay, and Reports

**Status:** COMPLETE (2026-09-10) — one command produces an immutable, verified bundle; replay reproduces the summary hash; a full 50-case fake run passes with no network.

## Goal

Connect validated suites, target invocation, deterministic evaluators, atomic run bundles, replay, aggregation, and JSON/Markdown reports behind one CLI command.

## Prerequisites and decisions

Phases 02 and 03 `COMPLETE`; ADR-005 accepted; filesystem artifact root and retention for local/CI runs approved.
**C-06 lock:** this phase writes exploratory bundles only. Do not read or write a baseline and do not emit `comparison.json`; baseline comparison is Phase 06.

## References and concepts

Read HLD §§3–4/8, LLD §§8–9/11, evaluation strategy §§5/9–10. Learn orchestration boundaries, bounded concurrency, immutable event/artifact records, atomic publication, replay, projections, percentiles, and experiment attribution.

## Files

- Create `src/eval_harness/application/{run,replay,aggregate}.py`, `adapters/artifacts/filesystem.py`, and `reporting/{json_report,markdown}.py`.
- Create run/result Pydantic schemas, schema version constants, and `evaluation/configs/fake.json`.
- Create `tests/unit/test_aggregation.py`, `test_reporting.py`; integration tests for run/replay/atomic publication/interruption; E2E fake-target test.
- Modify CLI `run`, `replay`, `inspect`, docs, and `Learning/concepts/05-runs-replay-experiments.md`.

## Interfaces produced

- `RunService.run(RunRequest) -> RunOutcome`.
- `ReplayService.replay(run_id) -> RunOutcome` without target calls.
- Immutable `RunManifest`, `AttemptRecord`, `CaseResult`, `Summary`, `BundleIndex` schemas.
- Complete run files: manifest, attempts, cases, summary, comparison placeholder only when requested, report, and `COMPLETE` index marker.

## Tasks

- [x] Test run state transitions, stable case ordering, selector semantics, partial-run non-release status, and bounded concurrency.
- [x] Implement runner composition without baseline or judge behavior; required semantic dimensions return review state.
- [x] Test atomic writer for exclusive run IDs, interruption at every file boundary, hash verification, existing target, permissions, and corrupted reads.
- [x] Implement canonical JSON/JSONL writer, staging/finalize lifecycle, and verified reader.
- [x] Test aggregates/percentiles against exact fixtures and prove report order does not affect scores.
- [x] Implement JSON and accessible Markdown projections from stored domain results only.
- [x] Implement replay from normalized outcomes and assert byte-equivalent scoring/summary hashes excluding permitted timestamps.
- [x] Wire CLI selectors, output formats, exit states, interruption, and report location.
- [x] Document changed-variable comparison metadata even though regression decisions arrive in Phase 06.

## Tests and failure scenarios

Process kill, disk full/permission error, duplicate run ID, corrupt/missing file, case timeout, incomplete case coverage, partial selector, unstable task completion order, report escaping, oversized evidence, replay under incompatible evaluator, and artifact root symlink escape.

## Verification

Run the Phase 04 unit/integration/E2E tests, then `python -m eval_harness run --suite evaluation/datasets/golden-v1 --config evaluation/configs/fake.json` and `python -m eval_harness replay --run <printed-run-id>`. Expected: 50 completed cases, valid bundle marker/hashes, matching replay scores, no network.

## Acceptance criteria and Definition of Done

One command runs all 50 fake cases, atomic publication prevents false completeness, replay reproduces scores, reports are projections, bounded concurrency preserves stable results, partial/incomplete runs cannot claim pass, docs/Learning/review complete, and phase reaches `COMPLETE`.

## Verification evidence (2026-09-10)

- `python -m eval_harness run --suite evaluation/datasets/golden-v1 --config evaluation/configs/fake.json` → `RUN … status=completed expected=50 completed=50 pass_rate=1.0` exit `0`.
- `python -m eval_harness replay --run <id>` → reproduces the stored summary hash; `inspect --failures-only` returns the bundle summary.
- `uv run pytest tests -q --cov=eval_harness` — **251 passed**; coverage **91%** (gate 85%).
- Tests cover: complete bundle files, duplicate run ID rejection, abandoned staging, adapter failure publishing nothing, corrupt bundle detection, selectors, replay hash equality, case `ERROR` for unusable outcomes, report escaping, and aggregation fixtures.
- `uv run ruff format --check .` / `uv run ruff check .` / `uv run mypy src/eval_harness` — clean (40 source files).
