# LLM-as-Judge

An LLM judge is a fallible measurement instrument. Narrow anchored rubrics improve interpretability. Strict structured output makes failures visible. Human calibration estimates agreement, repeatability, and slice bias before scores affect releases.

Judges should see only required, redacted evidence and must treat candidate text as data. Their rationales can help triage but do not make the score true. An unavailable, malformed, uncalibrated, or injection-compromised required judge yields uncertainty, not a silent pass.

## Phase 05 worked example — earning the right to gate

A judge scores exactly one dimension with an anchored 1–5 rubric mapped to `{1:0.0, 2:0.25, 3:0.50, 4:0.75, 5:1.00}` and a pass cut of `0.75`. It may influence a gate only after a frozen calibration slice meets all of:

| Check | Threshold |
|---|---|
| Adjudicated labels | ≥ 20, with both pass and fail present, ≥ 5 per gated rubric |
| Weighted Cohen's kappa (linear) | ≥ 0.70 |
| Exact pass/fail agreement | ≥ 0.80 |
| Three-run repeat agreement | ≥ 0.85 |
| Worst domain-slice gap | ≤ 10 points below overall |

The eligible fixture used in tests is human `[5,5,5,5,4,4,4,4,3,…]` versus judge `[5,5,5,4,4,4,4,3,3,…]`: kappa `0.875`, exact agreement `0.95`, repeat agreement `0.90`, worst slice gap `0.05`. That clears every bar; a five-label run does not, and returns `insufficient_labels`.

Fail-closed behavior is the point. If the calibration is a draft, missing, or for another rubric version, the judge contributes `JUDGE_UNCALIBRATED` and the case becomes `REVIEW_REQUIRED`. If the provider times out or returns malformed JSON, the result is `JUDGE_UNAVAILABLE` or `JUDGE_INVALID` — never a silent pass or a zero. A judge is also skipped entirely once a deterministic failure is decisive, so a fluent answer cannot override a forbidden tool call.

The repository ships rubrics and calibration machinery but **no approved calibration file**, because calibration requires real human labels and an approved provider. That gap is deliberate: the code is ready, the evidence is not.

Exercise: rewrite “Is this answer good?” into separate relevance, faithfulness, and completeness rubrics with anchored ordinal scores. Then decide what should happen when a calibrated judge fails a case whose deterministic checks all passed.
