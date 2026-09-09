# Phase 06 — Baselines, Regression Gates, and Statistics

**Status:** NOT_STARTED

## Goal

Implement explicit baseline promotion, compatibility checks, absolute/profile gates, paired case transitions, semantic non-inferiority evidence, operational budgets, and stable three-state decisions.

## Prerequisites and decisions

Phase 04 `COMPLETE`; Phase 05 `COMPLETE` for semantic gating; ADR-007 and ADR-012 accepted; the absolute target latency SLO chosen for the reference deployment before promotion.

## References and concepts

Read evaluation strategy §§6–8 and LLD §10. Learn baselines versus targets, paired designs, effect size, bootstrap intervals, non-inferiority, sample-size limitations, repetitions, uncertainty, threshold governance, and Simpson's/aggregate masking risk.

## Files

- Create `src/eval_harness/domain/{baselines,gates,statistics}.py`, `application/{compare,promote}.py`.
- Extend artifact repository for immutable baseline records and trusted pointer reads/writes.
- Create `evaluation/configs/gate-policy-v1.json` and approved baseline record after measured runs.
- Create unit tests for every threshold/boundary/decision reason, statistical fixtures, promotion/compatibility integration tests, and E2E candidate fixtures for all decision states.
- Modify CLI `compare`/`promote-baseline`, reports, docs, and `Learning/concepts/07-regression-statistics.md`.

## Interfaces produced

- `compare(candidate: RunBundle, baseline: RunBundle, policy: GatePolicy) -> Comparison`.
- `promote(run_id, suite, channel, reason, authorization) -> BaselineRecord`.
- Stable gate reason codes, ordered checks, paired bootstrap result, case/profile transitions, operational deltas, and `PASS|BLOCK|REVIEW_REQUIRED`.

## Tasks

- [ ] Write compatibility tests for suite/case/schema/evaluator/rubric/calibration/target-policy hashes and complete full-suite coverage.
- [ ] Implement immutable baseline record and explicit promotion with authorization evidence, predecessor link, atomic pointer update, and no implicit promotion.
- [ ] Write fail-first gate fixtures for each hard invariant, 45/50 boundary, each profile 80% boundary, 100% contract/safety, total/profile/new deterministic regression, and decision precedence.
- [ ] Implement ordered pure gate engine with complete reason evidence.
- [ ] Write exact paired bootstrap tests with injected seed, constant/empty/ineligible samples, known deltas, and reproducible 10,000 resamples.
- [ ] Implement non-inferiority and repeated-run majority/median aggregation without claiming external determinism.
- [ ] Add latency/cost absolute/relative budget tests and unavailable-data review behavior.
- [ ] Run/triage repeated reference executions and promote the first baseline only after every failure is reviewed.
- [ ] Wire compare/promotion CLI, reports, and audit-friendly baseline history.

## Tests and failure scenarios

Candidate missing cases, different suite/evaluator, corrupt baseline, candidate-controlled pointer, pass-count tradeoff across profiles, one new deterministic fail hidden by one improvement, confidence interval at `-0.05`, judge unavailable, provider runs disagree, latency/cost missing or on boundary, repeated promotion, concurrent pointer update, and interrupted write.

## Verification

Run Phase 06 unit/integration/E2E tests and all earlier checks. Execute fixture candidates expected to produce `PASS`/exit 0, `BLOCK`/exit 2, and `REVIEW_REQUIRED`/exit 3 with exact reason codes. Verify the approved baseline references immutable compatible artifacts.

## Acceptance criteria and Definition of Done

Promotion is explicit/protected/immutable, comparisons are paired and compatible, every documented threshold and uncertainty path is tested, a new deterministic failure always blocks, 50-case limitations are visible, all three decisions/exit codes work, the first baseline has review evidence, docs/Learning/review complete, and phase reaches `COMPLETE`.
