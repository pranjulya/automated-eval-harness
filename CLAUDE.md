# Project context

Project 07 is a learning-first Automated Eval Harness. It runs a versioned 50-case golden suite against a named GenAI target, scores deterministic and calibrated semantic dimensions, compares the candidate with an approved baseline, and blocks unsafe or statistically material regressions before deployment.

Authoritative documents:

- Product rules: `docs/product/PRD.md`
- Evaluation rules and thresholds: `docs/evaluation/evaluation-strategy.md`
- Dataset contract: `docs/evaluation/golden-dataset.md`
- Components and interfaces: `docs/architecture/HLD.md`, `docs/architecture/LLD.md`
- Execution order: `Implementation.md`, `implementation/`

Hard boundaries: no application code before approval; no mutable published artifacts; no judge-only safety or contract gate; no hidden configuration; no second evaluation path in CI/API/notebooks; no production data without explicit consent, redaction, retention, and access controls.

Follow `AGENTS.md`. Work one phase at a time and provide evidence before a completion claim.
