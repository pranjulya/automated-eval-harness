# Project 07 — Automated Eval Harness

A provider-neutral evaluation system for measuring GenAI quality against a versioned suite of 50 golden cases and blocking regressions before deployment.

**V1 scope (ADR-013):** the offline deterministic core is released — package, strict config, CLI, golden dataset, deterministic evaluators, target adapters, the runner with immutable bundles and replay, the gate engine with baselines/waivers, extension profiles, and the API/telemetry/online-sampling code. Semantic judge gating, repository protections, and the production identity/object-store wiring are deferred to post-V1 deployment enablement; the code for those is shipped and fails closed (`REVIEW_REQUIRED`). See `docs/operations/release-evidence.md`.

## Local development

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev            # create .venv and install locked dependencies
uv run pytest tests -q         # unit, contract, integration, and e2e tests
uv run ruff format --check .
uv run ruff check .
uv run mypy src/eval_harness
uv run python -m build         # build sdist + wheel

# Validate the golden suite
uv run python -m eval_harness validate \
  --suite evaluation/datasets/golden-v1 --config evaluation/configs/validation.json

# Run all 50 cases against the deterministic fake target
uv run python -m eval_harness run \
  --suite evaluation/datasets/golden-v1 --config evaluation/configs/fake.json
uv run python -m eval_harness replay --run <RUN_ID>
uv run python -m eval_harness inspect --run <RUN_ID> --failures-only

# Promote a reviewed run to a baseline channel, then compare a candidate
uv run python -m eval_harness promote-baseline --run <RUN_ID> --suite golden-v1 \
  --channel stable --reason "initial review" --approval-file approval.json
uv run python -m eval_harness compare --candidate <RUN_ID> --baseline stable --suite golden-v1
```

Runs are written under `EVAL_HARNESS_ARTIFACT_ROOT` (default `./artifacts/runs/<run-id>`).

Container (help/version only in Phase 00):

```bash
docker build -t eval-harness:dev .
docker run --rm eval-harness:dev --version
```

## Planning map

- Product contract: `docs/product/PRD.md`
- Evaluation policy: `docs/evaluation/evaluation-strategy.md`
- Golden data contract: `docs/evaluation/golden-dataset.md`
- Architecture: `docs/architecture/HLD.md`, `docs/architecture/LLD.md`, and `docs/architecture/threat-model.md`
- Readiness review: `docs/architecture/architecture-review.md`
- Pre-implementation gap analysis: `docs/architecture/planning-gap-analysis.md`
- Accepted decisions: `docs/architecture/decisions/`
- Extension profile authoring: `docs/architecture/extension-profiles.md`
- Failure triage: `docs/operations/failure-triage.md`
- CLI/API reference: `docs/operations/cli-api-reference.md`
- Service runbook: `docs/operations/service-runbook.md`
- Local run quickstart (not yet run): `docs/operations/local-quickstart.md`
- Release checklist: `docs/operations/release-checklist.md`
- Release evidence index: `docs/operations/release-evidence.md`
- Master roadmap: `Implementation.md`
- Executable phase specifications: `implementation/`
- Guided study material: `Learning/`

## V1 at a glance

- Exactly 50 curated, synthetic, non-sensitive golden cases in `golden-v1`.
- One CLI is the authoritative entry point; an HTTP API is a thin wrapper added later.
- Deterministic evaluators run first. LLM judges are optional, calibrated, versioned, and never decide hard safety or contract invariants.
- Every run records immutable inputs, configuration, raw outcomes, per-case scores, aggregates, costs, latency, and provenance.
- CI returns `PASS`, `BLOCK`, or `REVIEW_REQUIRED`; both `BLOCK` and `REVIEW_REQUIRED` stop deployment until resolved or explicitly waived.
- RAG, structured-output, and tool-use evaluation use profile-specific data inside one shared case/run contract.

## Deliberate V1 omissions

No dashboard SPA, custom workflow engine, distributed scheduler, SQL database, MLflow deployment, prompt-management SaaS, or automatic production optimization. Immutable filesystem/object-store artifacts and a small CLI cover the first release; add infrastructure only when measured scale or collaboration needs require it.

## Service surface

A thin FastAPI wrapper in `src/eval_harness/api.py` exposes the same application services as the CLI (runs, comparisons, baselines, online samples) with Bearer-token auth and role-based authorization. See `docs/operations/cli-api-reference.md`. Identity provider and object store are deployment selections; local defaults are documented in `docs/operations/service-runbook.md`.
