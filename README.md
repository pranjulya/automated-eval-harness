# Project 07 — Automated Eval Harness

A planning-first, provider-neutral evaluation system for measuring GenAI quality against a versioned suite of 50 golden cases and blocking regressions before deployment.

Implementation is underway one phase at a time. Phase 00 provides the installable package, strict configuration, CLI shell, and quality tooling; it contains no evaluation behavior.

## Local development

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev          # create .venv and install locked dependencies
uv run pytest tests/unit -q  # unit tests
uv run ruff format --check .
uv run ruff check .
uv run mypy src/eval_harness
uv run python -m build       # build sdist + wheel
uv run python -m eval_harness --help
uv run python -m eval_harness --version
```

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
- Failure triage: `docs/operations/failure-triage.md`
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
