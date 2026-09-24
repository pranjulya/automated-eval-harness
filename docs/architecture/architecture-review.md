# Architecture Review and Readiness Checklist

**Review result:** APPROVED_FOR_IMPLEMENTATION (user approval 2026-09-10); planning locks C-01–C-08 applied and ADR-001/ADR-002 accepted.  
**Reviewed scope:** Planning documents only.

Follow-up findings: `docs/architecture/planning-gap-analysis.md`. Independent review accepted the key locks in that file’s §11; owning documents were patched 2026-09-10. Remaining gaps stay open. It does not authorize application code.

## 1. Requirements and consistency

- [x] PRD, evaluation strategy, HLD, LLD, master plan, and phases agree on exactly 50 `golden-v1` cases and the 12/6/10/12/10 profile allocation.
- [x] CLI, API, and CI use one application/evaluation core.
- [x] Offline evaluation alone owns release authority; online signals require human curation.
- [x] Deterministic checks precede judges and hard invariants cannot be waived by judges.
- [x] Run, dataset, config, calibration, baseline, and waiver artifacts have immutable identities.
- [x] Phase dependencies are acyclic and every requested planning area maps to a document/phase.

## 2. Scope and simplicity

- [x] No application code, scaffold, dependency lock, or deployment config exists.
- [x] No custom queue, SQL database, dashboard SPA, workflow engine, plugin marketplace, or hosted tracker is required.
- [x] `argparse`, JSON/JSONL, hashing, atomic files, and artifact storage are preferred before new infrastructure.
- [x] RAG/structured/tool support extends evaluator contracts rather than forking the runner.
- [x] Fifty curated cases are not misrepresented as universal model proof.

## 3. Metrics and statistics

- [x] Metric formulas and edge behavior are explicit.
- [x] Overall scores are backed by case/profile/tag detail and hard invariants.
- [x] Candidate and baseline use paired cases.
- [x] Confidence evidence supplements, not replaces, deterministic case transitions.
- [x] The limitations of N=50 and external nondeterminism are documented.
- [x] Absolute floors, regression margins, latency/cost budgets, and threshold change control are defined.

## 4. Reproducibility and persistence

- [x] All material versions/hashes are enumerated.
- [x] Normalized-outcome replay can reproduce scoring without provider calls.
- [x] Partial writes cannot appear complete; readers verify the final bundle marker/hash.
- [x] Baseline pointers reference immutable runs and are protected from candidate writes.
- [x] Artifact-first persistence has a clear object-store upgrade and optional future catalog path.

## 5. Security and privacy

- [x] Dataset/target/judge/production content is untrusted.
- [x] No dynamic code/template execution is required.
- [x] Path containment, size limits, safe rendering, redaction, separate credentials, and least privilege are specified.
- [x] Production sampling is opt-in, redacted before persistence, quarantined, retention-bounded, and human-reviewed.
- [x] Hard invariants cover secret canaries, forbidden tools, citation identity, schema acceptance, and evidence isolation.

## 6. Operability

- [x] Stable CLI/API errors, statuses, and exit codes exist.
- [x] Logs/metrics/traces correlate stages without high-cardinality or raw sensitive payloads.
- [x] Failure taxonomy and triage ownership identify first failing layer.
- [x] Interrupted runs, provider/judge outages, corrupt artifacts, rate limits, and baseline attacks have defined behavior.
- [x] `REVIEW_REQUIRED` stops deployment until resolved or validly waived.

## 7. Testing and learning

- [x] Unit, property, contract, integration, E2E, calibration, security, and failure tests are mapped.
- [x] Paid/network provider tests are opt-in, never the default correctness suite.
- [x] Each phase has prerequisites, files, interfaces, tasks, tests, acceptance criteria, learning outcomes, and DoD.
- [x] Learning path, concepts, scenarios, and interview review are planned.

## 8. Known limitations accepted for V1

- The 50-case suite cannot measure tiny effects reliably or represent every future domain.
- External providers may not be exactly reproducible; manifests expose this and release runs use repetitions.
- Filesystem/object-store artifacts provide limited ad hoc querying until a catalog is justified.
- Online semantic drift detection depends on consent, sampling quality, human labels, and judge calibration.
- Cost estimates depend on versioned price/config inputs and may be unavailable for some targets.

## 9. Non-blocking deployment selections

The object store, identity provider, target provider, judge provider, absolute latency SLO, and exact dependency patch versions are selected at their named phases for the real deployment environment. Their contracts are fixed enough that these choices do not block planning review.

## 10. Approval gate

Implementation may begin one phase at a time. ADR-001/002 are accepted; Phase 00 moves to `IN_PROGRESS`, and no later phase starts before the preceding dependency and review gates pass.
