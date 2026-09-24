# Runs, Replay, and Experiments

An immutable run bundle is the experiment record: inputs, attempts, outcomes, findings, aggregates, comparison, and hashes. Atomic finalization keeps half-written evidence from appearing valid. Reports are projections; machine-readable records remain authoritative.

Replay applies current-compatible evaluators to recorded normalized outcomes. It helps find scoring bugs cheaply. A useful experiment changes one material variable, but multi-variable comparisons are allowed when marked non-attributable rather than given a false causal story.

## Phase 04 worked example — the bundle is the experiment

One `run` command writes this bundle:

| File | Role |
|---|---|
| `manifest.json` | Provenance and integrity: dataset hash, target identity, code commit, retry policy, concurrency. |
| `inputs.jsonl` | The exact selected `EvalCase` definitions. |
| `attempts.jsonl` | Raw evidence: every attempt with request/response hash, status, error, latency. |
| `outcomes.jsonl` | Recorded normalized outcomes — the replay input. |
| `cases.jsonl` | Per-case findings, state, latency, usage. |
| `summary.json` | Aggregates: pass rate, profile breakdowns, p95 latency, cost, comparability. |
| `report.md` | Human projection. Never the source of truth. |
| `COMPLETE` | Integrity marker written last, containing the index hash of every file. |

Publication is atomic: writes go to a hidden staging directory, each file is hashed, `COMPLETE` is written last, and the directory is renamed into place. `os.rename` fails if the run ID already exists, so a run ID is never overwritten. A process kill leaves only a staging directory that readers ignore, so a half-written run cannot be compared or promoted.

Replay recomputes findings and aggregates from `inputs.jsonl` + `outcomes.jsonl` and asserts the summary hash equals the stored one. It does not call the target. This is the cheap test for "did an evaluator version change scoring?" — a scoring bug shows up as a replay hash mismatch, not as a provider call.

Exercise: inspect a conceptual bundle and identify which files are raw evidence, decisions, projections, and integrity markers. Then explain why `report.md` must never be the only stored result.
