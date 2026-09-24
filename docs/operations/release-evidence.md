# Release Evidence Index

**Release candidate:** `main` (Project 07 Automated Eval Harness, V1)
**Evidence date:** 2026-09-10
**Overall status:** V1_CORE_ACCEPTED (2026-09-10, ADR-013) — the offline deterministic core is released.
Phases 00–04, 06, 09, and 10 are `COMPLETE`; Phases 05/07/08 are `DEFERRED_POST_V1` and listed below.

Every item links to reproducible commands or committed tests. No paid provider,
credential, or network is required for the deterministic evidence.

## Build and packaging
- Locked install: `uv sync --extra dev --frozen` from `uv.lock` (Python 3.12).
- Build: `uv run python -m build` → `eval_harness-0.1.0.tar.gz` + wheel.
- Clean wheel install verified in a fresh venv; console script and `python -m eval_harness` both work.
- Container: `.github/workflows/ci.yml` `container` job builds and runs `--version`/`--help` as non-root (CI green).

## Quality gates
- `uv run ruff format --check .` — clean.
- `uv run ruff check .` — clean.
- `uv run mypy src/eval_harness` — clean (59 source files).
- `uv run pytest tests -q` — **414 passed**; coverage **89.30%** (gate 85%).
- CI on `main`: `quality` and `container` green.

## Evaluation evidence
- `validate` → `OK golden-v1 1.0.1 cases=50 hash=e02461af…` exit `0`.
- 50-case fake run → `status=completed expected=50 completed=50 pass_rate=1.0`.
- `replay` → reproduces the stored summary hash; wall time ≈ 0.14 s for 50 recorded cases (10 s budget).
- Artifact bundle size ≈ 112 KB for 50 cases.
- Gate engine tests cover every reason code and boundary; e2e yields `PASS`/`BLOCK`/`REVIEW_REQUIRED`.
- CLI smoke: `run → promote-baseline → run → compare` = `PASS` exit `0`.
- `eval-release` gate: `REVIEW_REQUIRED` without a trusted baseline; `deploy` skipped.

## Security and privacy
- Hard-invariant tests: forbidden tool, secret canary, citation identity, evidence boundary, schema acceptance.
- Failure/security drills: `tests/e2e/test_production_drills.py` (timeout/rate-limit/malformed, corruption, partial write, aborted process, injection, baseline substitution, hard-invariant waiver abuse, PII redaction).
- Redaction catalog strips tokens, `Authorization` headers, secret canaries, and emails before persistence.
- Metric labels are allowlisted; `case_id`/`run_id`/`prompt`/`tenant` are rejected to bound cardinality.
- Waivers are scoped, GitHub-approved, expiring (≤14 days), and non-hard only.

## Architecture review
- `docs/architecture/architecture-review.md` re-run with evidence links; no unresolved blocker.
- ADR-001 … ADR-012 accepted (005/006/008/009/010 note deployment-selected values).

## Immutability and provenance
- `golden-v1` 1.0.1 content-addressed; corrections recorded in `REVIEW.md`.
- Run bundles atomic (staging → hash index → `COMPLETE` → rename); baselines immutable with predecessor links.
- Attestations bind commit, run-manifest hash, baseline hash, workflow, decision, and TTL.

## Deferred to post-V1 deployment enablement (ADR-013)
| Item | Phase | Owner action |
|---|---|---|
| Judge calibration labels + approved provider | 05 | ≥20 adjudicated labels; select provider; publish `evaluation/calibrations/**` |
| Branch protection, required reviewers, CI credentials | 07 | Configure repo/environments to make the deploy stop non-bypassable |
| OIDC issuer/JWKS, object store, retention/consent values | 08 | Select products; wire dashboards |
| Deployment-pipeline scans and escalation rehearsal | 10 | Add dependency/container/secret/license/SBOM scans |

## Reproduction

```bash
uv sync --extra dev --frozen
uv run pytest tests -q --cov=eval_harness
EVAL_HARNESS_ARTIFACT_ROOT=/tmp/eh uv run python -m eval_harness run \
  --suite evaluation/datasets/golden-v1 --config evaluation/configs/fake.json
EVAL_HARNESS_ARTIFACT_ROOT=/tmp/eh uv run python -m eval_harness replay --run <RUN_ID>
```
