# Product Requirements Document

**Product:** Project 07 — Automated Eval Harness  
**Status:** PROPOSED_FOR_REVIEW  
**V1 promise:** Every candidate GenAI release is measured against the same 50 versioned golden cases, and an explainable quality gate stops regressions before deployment.

## 1. Problem

Manual spot checks are inconsistent, easy to cherry-pick, and poor at locating the source of a failure. GenAI output also mixes deterministic correctness, probabilistic quality, operational reliability, and application-specific safety. A release process needs repeatable inputs, explicit scoring policies, stable baselines, traceable configuration, and a gate that fails safely when evidence is incomplete.

## 2. Product principles

1. Measure the smallest meaningful layers independently; never hide a contract or retrieval failure inside an average answer score.
2. Prefer deterministic checks. Use calibrated LLM judges only where semantics cannot be scored adequately with rules.
3. Compare paired cases against a reviewed baseline; do not compare unrelated aggregate snapshots.
4. Make artifacts immutable and self-describing so a run can be audited and replayed.
5. Treat `REVIEW_REQUIRED` as deployment-blocking, not as success.
6. Do not let production traffic silently rewrite quality policy.

## 3. Personas

| Persona | Need | Primary actions |
|---|---|---|
| AI engineer | Compare prompts, models, retrieval, and tools without guesswork | validate suite, run candidate, inspect case deltas |
| Application engineer | Protect structured/API contracts | add deterministic assertions, run locally, fix failures |
| Reviewer/quality owner | Understand why a release passed or stopped | review reports, calibrate rubrics, approve baseline/waiver |
| Release engineer | Consume a stable machine decision | run CI gate, publish artifacts, prevent deploy on block/review |
| Security/privacy reviewer | Prevent sensitive or unsafe evaluation flows | review datasets, retention, redaction, access, canaries |
| Product/domain expert | Curate correct representative goldens | label cases, review semantic disagreements and drift |

## 4. Goals

1. Ship a curated suite of exactly 50 synthetic, non-sensitive golden cases.
2. Evaluate text/semantic, safety/abstention, structured-output, RAG, and tool-use behaviors through one extensible contract.
3. Separate invocation, deterministic correctness, semantic quality, operational cost/latency, and gate decisions.
4. Reproduce scores from recorded normalized outcomes without another provider call.
5. Track every material dataset, prompt, model, tool, schema, evaluator, judge, rubric, and environment version.
6. Produce human-readable and machine-readable reports with per-case root-cause evidence.
7. Enforce absolute quality floors and baseline non-regression in CI.
8. Support controlled online sampling for drift discovery without making online signals release authority.
9. Teach evaluation design, statistics, reproducibility, and production failure handling.

## 5. Non-goals

- A general-purpose annotation SaaS, experiment marketplace, prompt IDE, model router, or production observability platform.
- Training, fine-tuning, reinforcement learning, automatic prompt rewriting, or automatic model selection.
- Automatically converting production traces into golden truth.
- Proving broad model capability from 50 cases or replacing domain-expert review.
- A custom statistics framework, distributed task queue, SQL warehouse, dashboard SPA, or mandatory third-party experiment tracker in V1.
- Judge scores as the sole basis for security, safety, schema, tool authorization, citation identity, or data-isolation decisions.
- Guaranteed bit-for-bit reproduction of external providers that do not expose stable model versions or deterministic inference.

## 6. V1 golden-suite composition

| Primary profile | Cases | Representative behavior |
|---|---:|---|
| Text/semantic | 12 | exact facts, normalized values, required concepts, concise synthesis, ambiguity |
| Safety/abstention | 6 | missing evidence, prohibited disclosure/action, injection resistance, appropriate refusal |
| Structured output | 10 | parseability, schema, types, enums, extra fields, business constraints |
| RAG | 12 | retrieval ranks, distractors, multi-source evidence, grounding, citations, no-answer |
| Tool use | 10 | tool choice, argument correctness, ordering, termination, forbidden tool/action |
| **Total** | **50** | one primary profile per case; cross-cutting tags allowed |

The suite is intentionally small enough for every failure to be reviewed and large enough to expose layer-specific regressions. Growth beyond 50 belongs in separately versioned extended/nightly suites, not by mutating `golden-v1`.

## 7. Primary journeys

### Local candidate check

An engineer validates the suite/config, runs a named target, receives a run ID and summary, opens failed case details, and exits with a stable status code.

### Pull-request gate

CI fetches the trusted baseline from the base branch, runs the 50 cases in an isolated environment, compares paired results, uploads the immutable bundle, and allows deploy only on `PASS`.

### Baseline promotion

A quality owner reviews the passing candidate, verifies configuration and known trade-offs, and creates a new baseline pointer through a protected change. Historical baselines and runs remain addressable.

### Regression triage

A reviewer filters newly failing cases, sees the first failing layer and candidate/baseline evidence, assigns a failure class, and links the remediation or approved time-bounded waiver.

### Online drift discovery

The service samples eligible, consented, redacted production outcomes, calculates deterministic operational/contract signals, and sends uncertain examples to a human labeling queue. Only a reviewed dataset change can enter an offline suite.

## 8. Functional requirements

- **FR-01:** Load a named suite only when its manifest, schema version, case count, unique IDs, referenced fixtures, and content hash validate.
- **FR-02:** Reject unknown fields by default and return stable path-specific validation errors.
- **FR-03:** Run one case, a tag/profile slice, or all 50 cases in stable case-ID order; support bounded parallel invocation without changing report order.
- **FR-04:** Invoke the target through a typed adapter and normalize success, timeout, transport/provider failure, malformed output, usage, latency, text, structured value, citations, evidence ranks, and tool trace.
- **FR-05:** Retry only failures declared safe by the adapter policy and record every attempt.
- **FR-06:** Apply deterministic evaluators before any judge call and short-circuit dimensions that cannot be meaningfully judged.
- **FR-07:** Calculate text, structured, RAG, tool-use, safety, latency, token, and cost measures defined by the evaluation strategy.
- **FR-08:** Invoke only calibrated, versioned judge rubrics and validate judge responses strictly.
- **FR-09:** Store a complete immutable run bundle and finalize it atomically.
- **FR-10:** Replay a run from normalized outcomes to reproduce evaluation and gate decisions without invoking the target.
- **FR-11:** Compare candidate and baseline case-by-case, aggregate by primary profile/tag, calculate defined confidence evidence, and return stable reasons.
- **FR-12:** Return exactly one decision: `PASS`, `BLOCK`, or `REVIEW_REQUIRED`.
- **FR-13:** Use stable exit codes: `0 PASS`, `2 BLOCK`, `3 REVIEW_REQUIRED`, `4 invalid/non-comparable run`, `5 infrastructure/internal failure`.
- **FR-14:** Create baseline pointers only through an explicit authorized promotion command; never during normal run/compare.
- **FR-15:** Generate `summary.json`, `cases.jsonl`, `manifest.json`, and `report.md` with compatible schema versions; complete release runs also generate `comparison.json`, while exploratory runs without a baseline are explicitly non-release.
- **FR-16:** Expose CLI contracts for validate, run, replay, compare, promote-baseline, and inspect.
- **FR-17:** Expose later HTTP contracts for creating a run, reading run status/results, comparing, and reading baselines; mutation remains access-controlled.
- **FR-18:** Emit structured logs, bounded metrics, and traces linked by run/case/attempt IDs without raw sensitive payloads.
- **FR-19:** Support explicit redaction, encrypted/quarantined sensitive artifacts, retention classes, and deletion of online samples where required.
- **FR-20:** Preserve extension profile data without letting profile-specific code fork the run lifecycle.
- **FR-21:** Require a reason, owner, scope, expiry, and approval identity for a waiver; never waive a hard invariant in V1.
- **FR-22:** Verify the trusted baseline came from the protected base branch or configured trusted store, not candidate-controlled content.

## 9. Non-functional requirements

- **Reproducibility:** complete material version/hash fields; deterministic replay; stable case order and aggregation.
- **Reliability:** atomic artifact publication; bounded retries; partial runs are explicit and non-comparable.
- **Performance:** local deterministic replay of 50 recorded cases completes within 10 seconds on a typical developer machine; live-run latency is dominated by target/provider calls and respects configured concurrency/rate limits.
- **Scalability:** streaming JSONL processing and bounded workers support later larger suites without changing contracts.
- **Portability:** Linux/macOS local use and clean container/CI execution; no cloud dependency for deterministic tests.
- **Maintainability:** profile evaluators are registered by type; the runner, gate engine, and persistence lifecycle remain shared.
- **Auditability:** baseline, waiver, threshold, rubric, and dataset changes are versioned and attributable.
- **Accessibility:** generated reports use semantic headings/tables and do not communicate status by color alone.

## 10. Security and privacy

- Treat cases, fixtures, target output, evidence, citations, tool arguments, and judge output as untrusted.
- Never execute dataset content, arbitrary commands, tool calls, templates, or code from target output.
- Enforce path containment, size/count limits, timeouts, output limits, schema rejection, and safe rendering.
- Keep provider credentials out of prompts, run artifacts, logs, reports, and test fixtures.
- Use least-privilege credentials separated for target and judge providers.
- Default V1 goldens to synthetic data. Production sampling is opt-in, policy-scoped, redacted before persistence, encrypted when retained, access logged, and retention-bounded.
- Defend against prompt injection in RAG evidence and judge prompt manipulation by strict instruction/data separation and output schemas.
- Hashes provide identity/integrity evidence, not secrecy; sensitive artifacts still require encryption and access control.

## 11. Success metrics

- 100% of valid release runs record all required provenance fields.
- 100% of seeded deterministic metric fixtures match hand calculations.
- All known hard-invariant breaches block.
- All three decision states are exercised by automated fixtures with stable reason codes.
- Recorded-outcome replay reproduces per-case and aggregate scoring.
- A newly failing deterministic golden case cannot reach the deploy job.
- Every failed case identifies a first failing layer and stable failure class.
- Judge calibration meets the documented agreement/repeatability policy before semantic scores can gate.
- The complete fake-target 50-case run succeeds without network or paid-provider access.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Golden overfitting | keep holdout/extended suite later; review case diversity and tag slices |
| Noisy labels | dual review for semantic goldens, disagreement log, immutable revisions |
| Judge bias/drift | frozen calibration slice, versioned judge/rubric, repeated checks, human review |
| Aggregate score hides harm | hard invariants, per-profile floors, paired case transitions |
| Provider nondeterminism | record exact config, repetitions, replay normalized outcomes, uncertainty state |
| Candidate manipulates baseline | protected base-branch/trusted-store resolution and signature/hash verification |
| Sensitive evaluation data leaks | synthetic default, redaction, quarantine, encryption, retention/access policy |
| CI becomes slow/costly | 50-case PR suite, recorded/fake tests by default, bounded concurrency and budgets |

## 13. Release gate

V1 is releasable only after the 50-case suite, deterministic metrics, target adapters, immutable bundles, judge calibration, baseline comparison, statistical policy, CI block, access controls, observability, extension proofs, clean-container run, and failure/security drills meet their phase Definitions of Done. This planning package authorizes no application code or deployment.
