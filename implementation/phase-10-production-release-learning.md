# Phase 10 — Production Drills, Packaging, Documentation, and Learning Release

**Status:** REVIEWED (2026-09-10) — drills, docs, evidence index, and architecture re-run complete; final `COMPLETE` requires release-owner acceptance and the open Phase 05/07/08 external gates.

## Goal

Verify the whole product in a clean environment, rehearse production failures/security controls, complete operator/developer/learning documentation, and re-run architecture readiness with evidence.

## Prerequisites and decisions

Phase 09 `COMPLETE`; deployment target, release configuration, ownership/on-call path, retention/budget/SLO values, and all required ADRs accepted.

## References and concepts

Read all authoritative docs, the failure playbook, phase evidence, and Learning path. Learn release evidence, recovery drills, runbooks, SLOs, incident roles, supply-chain/container controls, architecture conformance, and explaining deliberate omissions.

## Files

- Finalize `README.md`, operator/developer guides, API/CLI reference, runbooks, security/privacy/retention documentation, and architecture review evidence.
- Finalize Docker/release workflow and generated example reports without sensitive data.
- Complete all `Learning/` concepts, scenarios, learning path, and interview answers.
- Add clean-install/smoke/E2E/failure/security/performance tests and release checklist.
- Modify `Implementation.md` and phase statuses only from verified evidence.

## Interfaces produced

- Supported installation/run/upgrade/recovery contracts.
- Operator runbook for non-pass decisions, provider/storage outages, artifact recovery, waiver/promotion, privacy deletion, and rollback.
- Final release evidence index linking tests, runs, baseline, calibration, container, CI, security, and architecture review.

## Tasks

- [x] Build/install wheel and container from a clean checkout using only documented inputs; run help, validate, 50-case fake target, replay, compare, report, and API smoke paths. (Wheel + CLI + API smoke verified; container build verified by CI; a fully clean local container build remains a CI check.)
- [x] Execute every production scenario in `Implementation.md` and `Learning/scenarios/`, retaining safe evidence. (Scenarios 1–8 are covered by `tests/e2e/test_production_drills.py` and `tests/e2e/test_extension_profiles.py`.)
- [x] Inject provider/judge timeout/rate limit/malformed output, storage denial/partial write/corruption, process interruption, telemetry outage, baseline substitution, injection, secret/PII, and waiver abuse.
- [x] Measure deterministic replay time, live target p50/p95, cost/token reporting, artifact size, and bounded-concurrency behavior against declared budgets. (Replay ≈0.14 s, bundle ≈112 KB; live-provider numbers are a deployment measurement.)
- [ ] Scan dependencies/container/secrets/licenses, run as non-root, generate provenance/SBOM where the deployment policy requires it, and resolve blocking findings. (Non-root container done; dependency/secret/license/SBOM scanning is a deployment-pipeline task.)
- [ ] Verify operational dashboards/alerts and rehearse owner escalation, artifact restore, baseline rollback, and online-sample deletion. (Deletion/rollback paths tested in code; live dashboards and escalation are deployment tasks.)
- [x] Complete user/developer/operator/API/CLI/data-governance docs and ensure every command/schema/status is consistent. (`README`, `cli-api-reference`, `service-runbook`, `release-checklist`, `failure-triage`.)
- [x] Complete learning exercises and interview answers; demonstrate the system without reading generated code. (Concepts 01–10, scenarios, learning path, interview set complete.)
- [x] Re-run `docs/architecture/architecture-review.md` with evidence links and resolve every blocker before final status.

## Tests and failure scenarios

Fresh machine/container, unavailable network/provider/judge/object store, expired credentials, rate/cost limit, partial/corrupt run, incompatible historic schema, stale baseline, failed alert delivery, PII deletion, malicious fixture/output, large output, interrupted shutdown, and rollback to prior baseline/application version.

## Verification

Run the complete documented quality suite, clean package/container install, 50-case fake/reference runs, replay/compare/CI gate, API/security/privacy suites, scans, load/budget check, failure drills, and architecture review. Record exact commands, versions, results, and artifact hashes in the release evidence index.

## Acceptance criteria and Definition of Done

Every project-level DoD item in `Implementation.md` passes with evidence; docs reproduce clean execution; production/security/privacy drills behave safely; no unresolved blocking scan/review issue remains; baseline/calibration/CI evidence is immutable; Learning demonstration is accepted; all statuses agree; user accepts the release; phase and project reach `COMPLETE`.

## Verification evidence (2026-09-10)

- `uv run pytest tests -q --cov=eval_harness` — **414 passed**; coverage **89.30%** (gate 85%).
- 50-case fake run `pass_rate=1.0`; replay reproduces the summary hash in ≈0.14 s; bundle ≈112 KB.
- CLI smoke: `validate`, `run`, `replay`, `inspect`, `compare`, `promote-baseline` all exercised; API smoke covered by `tests/unit/test_api.py`.
- Drills: `tests/e2e/test_production_drills.py` (13 cases) and `tests/e2e/test_extension_profiles.py` (24 cases).
- Architecture review re-run to `READY_FOR_USER_ACCEPTANCE`; evidence index at `docs/operations/release-evidence.md`.
- `uv run ruff format --check .` / `uv run ruff check .` / `uv run mypy src/eval_harness` — clean.

## Outstanding for final COMPLETE

- Release-owner acceptance of the evidence index.
- Deployment-pipeline tasks: dependency/container/secret/license/SBOM scans, live dashboards/alerts, escalation rehearsal.
- Phase 05 calibration labels/provider, Phase 07 repository protections/credentials, Phase 08 IdP/object store.
