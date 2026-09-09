# Phase 02 — Deterministic Evaluators and Metrics

**Status:** NOT_STARTED

## Goal

Implement pure, inspectable hard-invariant and profile evaluators with hand-calculated metric fixtures and stable finding codes.

## Prerequisites and decisions

Phase 01 `COMPLETE`; ADR-004 accepted; metric formulas/edge semantics in the evaluation strategy and LLD accepted.

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

- [ ] Write hand-calculated failing tests for normal, empty, duplicate, graded, boundary, and invalid-label metric inputs.
- [ ] Implement the minimum pure metric functions with documented types and deterministic ordering.
- [ ] Write failing hard-invariant tests for schema acceptance, forbidden tool/action, citation identity, evidence boundary, canary disclosure, and integrity findings.
- [ ] Implement cross-cutting invariant evaluators.
- [ ] Add text/safety/structured/RAG/tool evaluators one at a time, each driven by profile fixtures and stable evidence paths.
- [ ] Test case-state precedence: invocation error, hard fail, deterministic fail, required semantic unavailable, pass.
- [ ] Add metamorphic checks for case-order invariance, duplicate evidence collapse, monotonic K behavior, and stricter-threshold monotonicity.
- [ ] Document every metric's denominator, unavailable state, and interpretation.

## Tests and failure scenarios

Zero denominators, empty retrieval, fewer than K results, duplicate evidence, tied/graded ranks, invalid JSON, surprising Unicode/whitespace, regex limits, extra schema fields, tool loops, argument mismatch, citation without context, and multiple simultaneous failures. No evaluator may execute output or call a provider.

## Verification

Run `python -m pytest tests/unit/test_metrics.py tests/unit/evaluators -q`, property/metamorphic tests, and all earlier checks. Expected: every metric equals its reviewed hand calculation and stable snapshots contain no raw secret/candidate payload.

## Acceptance criteria and Definition of Done

Every deterministic V1 requirement maps to an evaluator/finding code; every metric has exact fixtures and edge semantics; hard invariants cannot be downgraded; evaluator order does not change results; no I/O/framework/provider dependency enters domain code; docs/Learning/diff review complete; phase reaches `COMPLETE`.
