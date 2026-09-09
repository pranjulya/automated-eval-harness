# Phase 03 — Target Adapters and Normalized Attempts

**Status:** NOT_STARTED

## Goal

Implement a deterministic fake target and generic HTTP target adapter that produce the same normalized attempt/outcome contract with bounded safe retries.

## Prerequisites and decisions

Phases 01 and 02 `COMPLETE`; the Phase 02 `NormalizedOutcome` contract is frozen; target request/response mapping and approved egress/secret rules documented; no provider-specific SDK is required.

## References and concepts

Read PRD FR-03–06, HLD §§2/8/10, LLD §5. Learn ports/adapters, transport versus semantic failure, idempotency/retry safety, rate limiting, timeouts, normalization, raw evidence handling, and credential separation.

## Files

- Create `src/eval_harness/adapters/targets/{base,fake,http}.py`, `application/invocation.py`, and target config models.
- Create `tests/contract/targets/test_target_contract.py`, `tests/unit/test_invocation.py`, `tests/integration/test_http_target.py` with a local test server.
- Create deterministic response fixtures for all five profiles and transport failures.
- Modify config/CLI validation, docs, and `Learning/concepts/04-adapters-and-nondeterminism.md`.

## Interfaces produced

- `TargetAdapter.invoke(case, config) -> AttemptResult`.
- Normalized attempt states and retry reason codes.
- `InvocationService.invoke(case, target, policy) -> InvocationRecord` retaining every attempt and one final normalized outcome when successful.
- Target identity containing adapter/version/endpoint identifier/request-template hash/model/config/seed-support fields.

## Tasks

- [ ] Write shared contract tests for text, structured, evidence/citations, tool traces, usage/latency, timeout, rate limit, target error, and malformed response.
- [ ] Implement the fake adapter from static case-keyed fixtures; add no network or scoring behavior.
- [ ] Write retry policy tests for default one attempt, explicit idempotent retry, maximum three, backoff bounds, interruption, and no retry of unsafe/semantic errors.
- [ ] Implement invocation service with injected clock/sleeper and attempt preservation.
- [ ] Implement generic HTTP request/response mapping, byte/time limits, redaction hooks, auth header secret reference, and local contract server tests.
- [ ] Record honest nondeterminism/version capability when the target cannot provide stable model identity or seed behavior.
- [ ] Document target adapter authoring and why an adapter never decides pass/fail.

## Tests and failure scenarios

DNS/connect/read timeout, 429 with/without retry hint, 4xx/5xx classification, invalid content type/JSON, huge body, missing usage/model fields, cancellation, duplicate attempts, secret in headers/error, and partial tool/evidence data. Default tests stay local and unpaid.

## Verification

Run `python -m pytest tests/contract/targets tests/unit/test_invocation.py tests/integration/test_http_target.py -q` and all earlier checks. Expected: fake and HTTP fixtures normalize identically; unsafe failures are not retried; secrets do not appear in captured logs/results.

## Acceptance criteria and Definition of Done

Both adapters satisfy one contract, every attempt is preserved, retries are bounded/explicit/safe, normalized output is strict, target identity is reproducible or honestly marked nondeterministic, redaction/limits hold, docs/Learning/review complete, no runner/judge/baseline logic appears, and phase reaches `COMPLETE`.
