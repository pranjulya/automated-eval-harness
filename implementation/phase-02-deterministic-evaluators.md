# Phase 02 — Deterministic Evaluators and Metrics

**Status:** COMPLETE (2026-09-10) — pure metrics match hand-calculated fixtures; hard-invariant and profile evaluators tested; `jsonschema` confined to the structured evaluator.

## Goal

Implement pure, inspectable hard-invariant and profile evaluators with hand-calculated metric fixtures and stable finding codes.

## Prerequisites and decisions

Phase 01 `COMPLETE`; ADR-004 accepted; metric formulas/edge semantics in the evaluation strategy and LLD accepted; add approved direct dependency `jsonschema` (Draft 2020-12) for structured-output validation only.

## References and concepts

Read evaluation strategy §§3/5/7 and LLD §§2/6/7. Learn validity versus quality, confusion matrices, ranking metrics, claim/citation distinctions, tool traces, aggregation leakage, and why deterministic evidence precedes judges.

## Files

- Create `src/eval_harness/domain/{outcomes,findings,metrics}.py`.
- Create `src/eval_harness/evaluators/{invariants,text,safety,structured,rag,tools}.py` and explicit registry.
- Create focused unit tests `tests/unit/evaluators/test_*.py` and `tests/unit/test_metrics.py`.
- Create hand-calculated fixtures in `tests/fixtures/metrics/`.
- Modify documentation and `Learning/concepts/03-metrics-and-failure-layers.md`.

## Interfaces produced

- Immutable `NormalizedOutcome`, `Finding`, `EvidenceHit`, `Citation`, `ToolCall`, and `Usage`.
- `Evaluator.evaluate(case, outcome) -> tuple[Finding, ...]`.
- Pure functions for pass rate, confusion metrics, Recall/Precision@K, MRR, nDCG, context recall, percentiles, and case-state derivation.
- Stable failure codes from the evaluation strategy.

## Tasks

- [x] Write hand-calculated failing tests for normal, empty, duplicate, graded, boundary, and invalid-label metric inputs.
- [x] Implement the minimum pure metric functions with documented types and deterministic ordering.
- [x] Write failing hard-invariant tests for schema acceptance, forbidden tool/action, citation identity, evidence boundary, canary disclosure, and integrity findings. (Integrity is a run/CI invariant; its finding is exercised in Phase 04.)
- [x] Implement cross-cutting invariant evaluators.
- [x] Add `jsonschema` in this phase, lock the version in the existing lockfile, and confine it to the structured evaluator. Domain modules remain free of that library.
- [x] Add text/safety/structured/RAG/tool evaluators one at a time, each driven by profile fixtures and stable evidence paths. Structured schema checks use Draft 2020-12. Text regex uses only trusted repository-authored patterns; do not compile target output as a pattern and do not claim a `re` timeout.
- [x] Test case-state precedence: invocation error, hard fail, deterministic fail, required semantic unavailable, pass.
- [x] Add metamorphic checks for case-order invariance, duplicate evidence collapse, monotonic K behavior, and stricter-threshold monotonicity.
- [x] Document every metric's denominator, unavailable state, and interpretation.

## Tests and failure scenarios

Zero denominators, empty retrieval, fewer than K results (Precision@K still divides by K), duplicate evidence, tied/graded ranks, invalid JSON, Draft 2020-12 extra fields, surprising Unicode/whitespace, untrusted regex rejected, tool loops, argument mismatch, citation without context, and multiple simultaneous failures. No evaluator may execute output or call a provider.

## Verification

Run `python -m pytest tests/unit/test_metrics.py tests/unit/evaluators -q`, property/metamorphic tests, and all earlier checks. Expected: every metric equals its reviewed hand calculation and stable snapshots contain no raw secret/candidate payload.

## Acceptance criteria and Definition of Done

Every deterministic V1 requirement maps to an evaluator/finding code; every metric has exact fixtures and edge semantics; hard invariants cannot be downgraded; evaluator order does not change results; no I/O/framework/provider dependency enters domain code; docs/Learning/diff review complete; phase reaches `COMPLETE`.

## Verification evidence (2026-09-10)

- `uv run pytest tests -q --cov=eval_harness` — **160 passed**; coverage **93%** (gate 85%).
- Hand-calculated fixtures for Recall/Precision@K, MRR, nDCG@K, pass rate, precision/recall/F1, percentiles, and context recall all match.
- Boundary/metamorphic tests: empty retrieval, no labels, short lists, duplicate collapse, K monotonicity, threshold monotonicity, invalid K, overshoot pass rate.
- `uv run ruff format --check .` and `uv run ruff check .` — clean.
- `uv run mypy src/eval_harness` — Success: no issues found in 23 source files.
- `jsonschema` is imported only by `evaluators/structured.py`; `domain/` imports no library.
