# ADR-006 — Semantic judging

**Status:** ACCEPTED (implementation gated on human calibration evidence)  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Some dimensions (relevance, faithfulness, completeness, citation support) cannot be scored by exact rules. Phase 05 must add semantic scoring without letting an uncalibrated or jailbroken model override deterministic evidence. The evaluation strategy §4 fixes the eligibility thresholds.

## Decision

Use narrow, rubric-specific, versioned judges. A judge scores exactly one named dimension, receives the minimum redacted evidence inside clear data delimiters, and must return strict structured output with an ordinal score, cited evidence IDs, and a short rationale. A judge may contribute to a release gate only after a frozen calibration slice meets: ≥20 adjudicated labels with both pass/fail present and ≥5 per gated rubric; weighted Cohen's kappa ≥0.70; exact pass/fail agreement ≥0.80; three-run repeat agreement ≥0.85; and no domain slice more than 10 points below overall. Judges never override a deterministic failure, and unavailable/invalid/uncalibrated required judging yields `REVIEW_REQUIRED`.

## Consequences

- Semantic scores are earned, not assumed; the harness ships no approved calibration without human labels.
- A judge outage degrades to review, never a silent pass or a zero score.
- Anchor mapping is data (`{1:0.0,2:0.25,3:0.5,4:0.75,5:1.0}`), not prompt text.
- Calibration costs human review time and gates the semantic path.

## Alternatives considered

- One "is this good?" overall-quality judge: rejected — unconstructive and unauditable.
- Majority vote of uncalibrated judges: rejected — no ground truth.
- Judge-only safety/schema checks: rejected — deterministic invariants must win.

## Compliance

`tests/unit/test_calibration_metrics.py` matches hand calculations; `tests/contract/judges/` proves strict output and fail-closed behavior; `tests/unit/test_judge_service.py` proves uncalibrated rubrics return `REVIEW_REQUIRED`. No `evaluation/calibrations/**` file is shipped until human labels exist.
