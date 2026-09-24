# Phase 01 — Golden Dataset Contracts and 50-Case Suite

**Status:** COMPLETE (2026-09-10) — 50 cases validate at the locked distribution; loader/security tests, hashing, and CLI `validate` verified locally.

## Goal

Implement strict case/suite schemas, safe loading, content hashing, fixture validation, and the reviewed `golden-v1` dataset containing exactly 50 cases in the locked profile distribution.

## Prerequisites and decisions

Phase 00 `COMPLETE`; ADR-003 accepted; dataset owners/reviewers named; repository `LICENSE` applies to synthetic fixtures; privacy classification accepted.

## References and concepts

Read PRD §§6/8/10, `docs/evaluation/golden-dataset.md`, LLD §4. Learn golden versus observed data, labeling error, immutable versioning, discriminated schemas, content addressing, path traversal defense, leakage/overfitting, and review governance.

## Files

- Create `src/eval_harness/domain/cases.py`, `datasets/models.py`, `datasets/loader.py`, `datasets/hashing.py`, `datasets/validation.py`.
- Create `evaluation/datasets/golden-v1/{manifest.json,cases.jsonl,checksums.json,REVIEW.md}`, minimal synthetic fixtures, and `evaluation/configs/validation.json`.
- Create `tests/unit/test_case_models.py`, `test_dataset_hashing.py`, `test_dataset_validation.py`.
- Create `tests/integration/test_golden_v1.py` and malicious fixture cases under `tests/fixtures/datasets/`.
- Modify CLI `validate`, docs, and `Learning/concepts/02-golden-datasets.md`.

## Interfaces produced

- `load_suite(path: Path, limits: DatasetLimits) -> LoadedSuite`.
- `validate_suite(path: Path, limits: DatasetLimits) -> ValidationReport`.
- Immutable `DatasetIdentity(name, suite_version, schema_version, content_hash, case_ids)`.
- Discriminated `EvalCase` union for the five profiles and canonical suite hashing.

## Tasks

- [x] Write failing model tests for unknown fields, profile-specific requirements, weights other than one, invalid IDs, contradictory answerability, and unresolved rubric/tool/schema references.
- [x] Write failing loader/security tests for duplicate IDs, count/profile mismatch, checksum mismatch, symlink/`..` escape, oversize/nesting limits, blank lines, malformed UTF-8/JSON, and secret/PII policy violations.
- [x] Implement strict models, streaming load, canonical hashes, containment, checksum, and validation report.
- [x] Author and dual-review 50 synthetic cases: 12 text, 6 safety, 10 structured, 12 RAG, 10 tool.
- [x] Add distribution/tag/duplicate/diversity checks and hand-review evidence in `REVIEW.md`.
- [x] Wire `validate` to print stable human/JSON reports and exit `4` on invalid data.
- [x] Document how to add, correct, supersede, and review a case without mutating a published suite.

## Tests and failure scenarios

All schema boundaries, missing fixtures, absolute paths, traversal/symlinks, huge records, duplicate content, mismatched manifest/checksum, wrong profile counts, unresolved versioned references, and synthetic privacy policy. The integration test asserts exactly 50 unique ordered IDs and the declared suite hash.

## Verification

Run `python -m pytest tests/unit/test_case_models.py tests/unit/test_dataset_hashing.py tests/unit/test_dataset_validation.py tests/integration/test_golden_v1.py -q`, full Phase 00 checks, and `python -m eval_harness validate --suite evaluation/datasets/golden-v1 --config evaluation/configs/validation.json`. Expected: valid, 50 cases, exact distribution, matching hash.

## Acceptance criteria and Definition of Done

All 50 cases are non-sensitive, reviewed, strictly valid, uniquely identified, fixture-contained, content-addressed, and profile-balanced as specified. Invalid/tampered suites fail before invocation. CLI, docs, review evidence, tests, Learning note, and diff review are complete; no evaluator/target/runner behavior is introduced; phase reaches `COMPLETE`.

## Verification evidence (2026-09-10)

- `python -m eval_harness validate --suite evaluation/datasets/golden-v1 --config evaluation/configs/validation.json` → `OK golden-v1 1.0.0 cases=50 hash=d6cc49a2…` exit `0`.
- Suite hash is idempotent across generator runs and matches `manifest.json`.
- `uv run pytest tests -q` — **89 passed**; coverage **93%** (gate 85%).
- `uv run ruff format --check .` and `uv run ruff check .` — clean.
- `uv run mypy src/eval_harness` — Success: no issues found in 12 source files.
- Tampered case files, duplicate IDs, count/profile mismatch, traversal/missing fixtures, uncovered files, oversize records, and nesting abuse all fail closed with exit `4`.
