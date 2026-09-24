# Phase 09 — Structured-Output, RAG, and Tool-Use Extension Proof

**Status:** COMPLETE (2026-09-10) — all 32 complex-profile goldens execute and diagnose through the shared runner; fake/HTTP parity and report diagnostics verified. (Blocked external parts of Phases 05/07/08 do not affect these deterministic profiles.)

## Goal

Prove that the three complex profiles work end-to-end through the shared runner, artifacts, gates, CLI/API, and CI without profile-specific orchestration forks.

## Prerequisites and decisions

Phases 02–08 `COMPLETE`; ADR-011 accepted; `golden-v1` fixtures and reference fake/HTTP target mappings reviewed.

## References and concepts

Read dataset design §4, evaluation strategy §3, HLD §7, LLD §§3/6–7. Learn schema/business validation, retrieval-stage attribution, ranking metrics, grounded claims/citations, no-answer evaluation, tool-call traces, partial orders, loop/forbidden-action safety, and shared lifecycle design.

## Files

- Complete first-party evaluators/models/report projections for structured, RAG, and tool profiles.
- Create profile E2E fixtures and tests for all 32 complex-profile goldens (`10+12+10`).
- Create adapter compatibility fixtures for evidence/citation/tool trace normalization.
- Modify API filters/reports/docs and update `Learning/concepts/10-extension-profiles.md`.

## Interfaces produced

- Final `StructuredExpectation`, `RagExpectation`, and `ToolExpectation` v1 schemas.
- Profile diagnostic sections within the existing `CaseResult`/report, not separate run formats.
- Stable profile failure codes and metric aggregates used by the same gate engine.

## Tasks

- [x] Structured E2E: valid nested output, wrong type/enum, extra field, missing field, range/business assertion, malformed/trailing output; prove schema-acceptance invariant.
- [x] RAG E2E: lexical/semantic/distractor/multi-document/no-answer cases; verify deduped Recall@K/MRR/nDCG eligibility, context recall, claim support, citation identity/correctness/completeness, and evidence boundary.
- [x] Tool E2E: expected/forbidden selection, exact/subset arguments, order/partial order, maximum steps, loops, termination, and recovery; prove forbidden call hard block.
- [x] Run all profiles through fake and HTTP normalized contracts; compare/replay without special runner paths.
- [x] Verify reports and API filtering expose profile evidence safely and gate profiles independently.
- [x] Add a new-profile compile-time/test example in docs without implementing a dynamic plugin loader.
- [x] Review evaluator performance and streaming/bounded-memory behavior across the 50-case suite. (Loader streams JSONL with per-record and nesting limits; evaluators are pure and linear.)

## Tests and failure scenarios

Invalid nested JSON, floating tolerance misuse, duplicated evidence, missing/graded labels, citation to retrieved-but-not-approved evidence, no-answer hallucination, cross-boundary hit, tool argument coercion, repeated calls, partial-order ambiguity, untrusted tool output injection, and profile result attempting to alter run lifecycle.

## Verification

Run all profile unit/contract/E2E tests, then the full 50-case fake and HTTP-local runs with replay/comparison. Expected: exact 12/6/10/12/10 aggregates, profile failures attributed correctly, hard invariants block, and one common bundle/schema/runner path.

## Acceptance criteria and Definition of Done

All complex goldens execute and diagnose correctly, metrics match hand labels, schema/tool/citation/isolation invariants hold, no profile forks lifecycle/persistence/gating, reports remain safe, docs/Learning/review complete, and phase reaches `COMPLETE`.

## Verification evidence (2026-09-10)

- `uv run pytest tests -q --cov=eval_harness` — **401 passed**; coverage **~89%** (gate 85%).
- `tests/e2e/test_extension_profiles.py`: all 32 complex cases pass; each structured/RAG/tool failure mode is attributed to its stable code with the correct severity; fake and HTTP normalize identically for all 32; replay and compare use no profile-specific path; the report renders the profile-diagnostics section.
- `docs/architecture/extension-profiles.md` documents the three extension points and the no-plugin rule.
- `uv run ruff format --check .` / `uv run ruff check .` / `uv run mypy src/eval_harness` — clean (59 source files).
