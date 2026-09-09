# Scenario 02 — Inconclusive Model Change

## Situation

A model alias change keeps deterministic pass counts unchanged. Mean calibrated semantic score falls slightly; the paired 95% interval crosses the `-0.05` non-inferiority margin. Provider responses vary across three repetitions.

## Expected evaluation

The report retains all repetitions, uses majority pass and median score, and records the alias/response model/date as externally nondeterministic. A raw decline with inconclusive evidence returns `REVIEW_REQUIRED`, which stops deployment.

## Triage

Owner: quality owner and domain reviewer. Inspect pass→fail dimensions, provider version evidence, and case-level distributions. Options are a justified rerun under the same immutable config, human adjudication, candidate rollback, or a narrow expiring non-hard waiver.

## Questions

Why does “not statistically significant” not mean “equivalent”? Why pair by case? When should the suite expand beyond 50 cases?
