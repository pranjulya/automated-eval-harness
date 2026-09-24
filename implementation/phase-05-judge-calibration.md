# Phase 05 — Semantic Judge Rubrics and Calibration

**Status:** DEFERRED_POST_V1 (ADR-013) — code and tests complete; semantic gating deferred pending human calibration labels and an approved judge provider. No approved calibration file is shipped.

## Goal

Add optional semantic scoring with strict rubric-specific judge contracts, human calibration evidence, repeated reliability checks, and fail-closed handling.

## Prerequisites and decisions

Phase 04 `COMPLETE`; ADR-006 accepted; judge provider/config chosen for calibration; domain reviewers and frozen calibration slice identified; paid calls explicitly approved for the calibration run.

## References and concepts

Read evaluation strategy §4 and PRD goals/non-goals/security. Learn construct validity, ordinal rubrics, inter-rater agreement, Cohen's kappa, judge bias/drift, prompt injection, structured judge output, and human adjudication.

## Files

- Create `src/eval_harness/domain/judging.py`, `application/judging.py`, `adapters/judges/{fake,http}.py`.
- Create `evaluation/rubrics/*.json`, `evaluation/calibrations/<rubric>/<version>.json` after review.
- Create judge contract/unit tests, calibration metric fixtures/tests, injection/malformed-output tests, and an opt-in provider calibration test.
- Modify run service, manifest/result schemas, reports, docs, and `Learning/concepts/06-llm-judges.md`.

## Interfaces produced

- `JudgeRequest` with one rubric/dimension and bounded redacted evidence.
- `JudgeResult` with ordinal/normalized score, pass mapping, evidence IDs, rationale, identity, and attempt metadata.
- `CalibrationRecord` with human labels, repeats, agreement/bias metrics, eligibility decision, reviewer evidence, and hashes.
- `JudgeService.score(case, outcome, rubric, calibration) -> SemanticFinding`.

## Tasks

- [x] Define anchored rubrics for relevance, faithfulness, completeness, and citation support; remove any generic overall-quality prompt.
- [x] Write fake/HTTP judge contract tests for strict structured output, identity, timeout/rate limits, malformed values, unknown evidence, injection, and redaction.
- [x] Implement eligibility checks that reject missing/mismatched/unapproved calibration.
- [x] Implement calibration calculations and tests for kappa, exact pass/fail agreement, three-run repeatability, and slice gaps.
- [ ] Produce at least 20 independent human case-dimension labels with both pass/fail and at least five per gated rubric, adjudicate disagreement, run approved judge repeats, and publish immutable calibration evidence. **Human gate — not started.**
- [x] Integrate semantic findings only for dimensions requested by cases; skip judges after decisive deterministic failure.
- [x] Make unavailable/invalid/uncalibrated required judging yield `REVIEW_REQUIRED`, never silent pass or zero score.
- [x] Add judge identity/usage/cost/latency to manifests and reports without sensitive content.

## Tests and failure scenarios

Uncalibrated rubric, model alias drift, changed prompt hash, schema-invalid output, unsupported score, invented evidence ID, rationales containing secrets, document instructions attacking rubric, provider outage, inconsistent repeats, low agreement, biased slice, and deterministic failure attempting judge override.

## Verification

Run all fake/local judge and calibration tests; run provider calibration only with the documented marker and approved credentials. Expected gating eligibility requires kappa `>=0.70`, exact pass/fail agreement `>=80%`, repeat agreement `>=85%`, and no slice gap above 10 points; otherwise judge remains informational.

## Acceptance criteria and Definition of Done

Rubrics are narrow and versioned, judge results are strict/untrusted, calibration is immutable and human-reviewed, eligibility thresholds are enforced, deterministic failures remain authoritative, failures expose uncertainty, cost/privacy controls hold, docs/Learning/review complete, and phase reaches `COMPLETE`.

## Verification evidence (2026-09-10) — code portion

- `uv run pytest tests -q --cov=eval_harness` — **281 passed**; coverage ~91% (gate 85%).
- Calibration fixture: kappa `0.875`, exact agreement `0.95`, repeat agreement `0.90`, worst slice gap `0.05` → eligible; five-label and inverted-judge cases are ineligible with explicit failure reasons.
- Judge contract tests cover fake + HTTP success, 5xx, malformed, oversize, missing secret, and secret non-disclosure.
- Service tests cover calibrated pass/fail, draft/missing calibration → `JUDGE_UNCALIBRATED`, outage → `JUDGE_UNAVAILABLE`, malformed → `JUDGE_INVALID`, redaction before judging, and decisive-failure skip.
- `uv run ruff format --check .` / `uv run ruff check .` / `uv run mypy src/eval_harness` — clean (46 source files).

## Outstanding blocker

`COMPLETE` requires real human adjudicated labels and an approved paid provider run to publish `evaluation/calibrations/**`. Until then, semantic gating stays informational and the runner leaves semantic-required cases at `REVIEW_REQUIRED`.
