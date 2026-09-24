# Reproducible Evaluation

Evaluation is a measurement pipeline, not a prompt script. The measured subject, inputs, procedure, instrument, environment, and decision policy all need identities. A run manifest binds those identities so another engineer can explain what changed.

Reproduction has two levels. Outcome replay proves that evaluators and gates produce the same result from the same normalized outcome. Live replay asks an external provider for another output and may differ even with temperature zero. The harness records that limitation instead of promising determinism it does not control.

## Phase 00 worked example — boundaries before behavior

The foundation layer deliberately contains no evaluation logic. It fixes the boundaries every later phase depends on:

- **One installable package** (`src/eval_harness`) with `requires-python = ">=3.12"` and a committed `uv.lock`, so local, CI, and container runs resolve identical dependencies (ADR-001).
- **Strict startup config** resolved only from `EVAL_HARNESS_*` variables. Unknown keys fail; production + `DEBUG` fails; secrets are stored as *environment-variable names* and their values are read only for redaction (ADR-002, G-25).
- **One error envelope** `{code, message, retryable, details}` with a locked exit map: `0` success, `2` BLOCK, `3` REVIEW_REQUIRED, `4` invalid, `5` internal, `130` interrupted (PRD FR-13).
- **One authoritative CLI** using standard-library `argparse`; reserved subcommands fail closed with `PHASE_UNAVAILABLE` until their owning phase exists. The HTTP API added in Phase 08 will call the same application services, never a second evaluator.

Why this ordering matters: if the exit-code map or secret handling were invented inside a framework route or a later phase, two entry points could disagree about what "blocked" means. Fixing the boundary first makes every later decision comparable.

Exercise: list every material field needed to distinguish a model change from a prompt, schema, retrieval, evaluator, or environment change. Then add the one boundary you would fix first if you could only fix one, and justify it.
