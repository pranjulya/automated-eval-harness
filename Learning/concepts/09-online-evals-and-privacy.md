# Online Evaluation and Privacy

Offline evaluation answers “may we release this candidate?” Online evaluation asks “is production behavior drifting or revealing new failure modes?” Traffic is not automatically labeled truth. Sampling can be biased and production data can contain personal, confidential, or regulated information.

Consent and eligibility precede collection; redaction precedes persistence; quarantine restricts uncertain data; retention and deletion are enforceable. Human review turns a sanitized observation into a proposed golden case through normal versioning.

## Phase 08 worked example — one core, thin surfaces

The HTTP API is a translation layer. `POST /v1/runs` calls the same `RunService` the CLI calls, and a test asserts that the API's aggregate summary equals a direct service call. There is no second evaluator or gate engine.

Trust rules that the code enforces:

- **Actor comes from the token, never the body.** The promotion route records `Principal.actor`; a client cannot claim to be someone else.
- **Roles gate actions.** `reader` can read runs/comparisons/baselines; `runner` can create runs; `quality_owner` can review samples and promote; `security_admin` can delete quarantined samples. A missing token is `401`, an insufficient role is `403`.
- **Metric labels are an allowlist.** `case_id`, `run_id`, `prompt`, `tenant`, and raw model names are rejected as labels so cardinality stays bounded; they belong in logs/traces.
- **Online samples are inert.** `submit` requires consent, redacts *before* persistence, and stores the candidate as `quarantined`. `propose_draft_case` returns a redacted draft and nothing more; there is no code path from a sample to a published dataset, rubric, threshold, or baseline.

The local object store mirrors the filesystem bundle contract (immutable content-addressed objects, `COMPLETE` written last, integrity-checked reads), so the storage backend is swappable without changing evaluation semantics. The production object store and identity provider are deployment selections.

Exercise: trace a production response containing an email, account ID, and secret-like token through sample rejection, redaction/quarantine, access, retention, and deletion. Then explain why a metric labelled by tenant or case ID is a privacy and cost problem.
