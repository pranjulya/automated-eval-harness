# Release Checklist

Use for every V1 release. Record the results in `docs/operations/release-evidence.md`.

## 1. Source and build
- [ ] Clean checkout at the release commit; no uncommitted changes.
- [ ] `uv sync --extra dev --frozen` succeeds from `uv.lock`.
- [ ] `uv run python -m build` produces wheel + sdist.
- [ ] Wheel installs into a fresh venv; `eval-harness --version` works.
- [ ] Container builds and runs `--version` as a non-root user.

## 2. Quality gates
- [ ] `uv run ruff format --check .` clean.
- [ ] `uv run ruff check .` clean.
- [ ] `uv run mypy src/eval_harness` clean.
- [ ] `uv run pytest tests -q` passes with coverage ≥ 85%.
- [ ] CI `quality` and `container` jobs green on the release commit.

## 3. Evaluation readiness
- [ ] `validate` reports exactly 50 cases and prints the suite hash.
- [ ] 50-case fake run reaches `completed=50`.
- [ ] `replay` reproduces the summary hash.
- [ ] Baseline promoted through the protected workflow; comparison against it is `PASS`.
- [ ] `eval-release` gate attestation verifies for the exact commit.

## 4. Security and privacy
- [ ] No secrets in artifacts, logs, reports, or fixtures.
- [ ] Hard-invariant drills block (forbidden tool, secret canary, citation identity, evidence boundary, schema).
- [ ] Online samples require consent, are redacted before persistence, and cannot auto-publish.
- [ ] Waivers are scoped, approved, expiring, and non-hard only.

## 5. Operability
- [ ] Failure drills pass (`tests/e2e/test_production_drills.py`).
- [ ] Readiness reports artifact-store state without corrupting decisions.
- [ ] Baseline promotion is attributable and reversible (new pointer, history retained).
- [ ] Retention/purge and deletion-evidence paths exercised.

## 6. Acceptance
- [ ] Architecture review re-run with evidence links; no unresolved blocker.
- [ ] Learning material complete; system demonstrated without reading generated code.
- [ ] Release owner accepts the evidence and records the decision.
