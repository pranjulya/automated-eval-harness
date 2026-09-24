# ADR-007 — Regression policy

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Phase 06 must turn per-case results into one deploy decision. Aggregate-only comparisons hide layer failures; p-values alone do not answer “is the candidate non-inferior?”. The evaluation strategy §§7–8 fix the thresholds and statistics.

## Decision

Compare a candidate to a trusted baseline with ordered checks: integrity/compatibility → hard invariants → absolute floors (overall ≥ 0.90, each profile ≥ 0.80, safety and contract validity = 1.00) → paired case and profile non-regression → paired bootstrap semantic non-inferiority (95% lower bound ≥ −0.05, 10,000 draws, recorded seed, < 10 paired semantic cases is insufficient) → absolute and relative latency/cost budgets. Decision priority is `BLOCK` over `REVIEW_REQUIRED` over `PASS`. A newly failing deterministic case always blocks. Thresholds live in `evaluation/configs/gate-policy-v1.json`, never in CI YAML.

## Consequences

- Every decision exposes ordered, stable reason codes and case transitions.
- Fifty cases have coarse power; the interval supplements case transitions and never excuses a hard failure.
- Threshold changes are versioned policy changes requiring a new baseline review.

## Alternatives considered

- Aggregate-only threshold: rejected — hides per-profile and per-case regressions.
- p-value-only decision: rejected — does not express non-inferiority or uncertainty honestly.
- Candidate recomputes its own threshold: rejected — release policy must be reviewed data.

## Compliance

`tests/unit/test_gates.py` exercises every reason code and boundary; `tests/unit/test_statistics.py` matches hand-calculated bootstrap results; `tests/e2e/test_decision_states.py` produces all three decisions.
