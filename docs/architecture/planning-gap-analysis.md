# Planning Gap Analysis — Pre-Implementation Findings

**Status:** KEY_LOCKS_APPLIED — independent review accepted the items in §11; owning docs patched 2026-09-10. Still not an ADR and not authorization to write application code.  
**Date:** 2026-09-09 (locks applied 2026-09-10)  
**Author:** Grok planning audit  
**Audience:** Independent reviewer (including Codex). Remaining open gaps in §2 still need later-phase locks. Do not start application code from this list.

This document captures a consolidated audit of the current repository. It is a review artifact, not a product-rule change. Authoritative documents remain `docs/product/PRD.md`, `docs/evaluation/evaluation-strategy.md`, `docs/evaluation/golden-dataset.md`, `docs/architecture/HLD.md`, `docs/architecture/LLD.md`, and accepted ADRs. When this file conflicts with those documents, **do not implement from this file**; repair the owning document first.

## Reviewer brief

Please review:

1. Whether each **contradiction** is real and which proposed lock is correct.
2. Whether each **spec gap** must be closed before its named phase, or can wait.
3. Whether the **50-case coverage map** is complete enough to author `golden-v1`.
4. Whether any recommended process file is out of scope for V1.
5. That **Do not add in V1** still matches the PRD non-goals.

Record findings as accept / revise / reject per numbered item. Do not start application code from this list.

## Current repository state

| Area | What exists | Status |
|---|---|---|
| Product / eval / architecture docs | PRD, strategy, dataset contract, HLD, LLD, threat model, architecture review | Proposed for review |
| Decisions | `docs/architecture/decisions/ADR-candidates.md` only | Not accepted |
| Phases 00–10 | Specs only | All `NOT_STARTED` |
| Learning | 10 concepts, 5 scenarios, interview Q&A | Outline-level |
| Application code | None | Correct until user approval |
| Dataset / configs / rubrics / baselines | None | Phase 01+ |
| Git | `origin/main` at GitHub `pranjulya/automated-eval-harness` | Present; dirty-flag provenance still requires a clean Phase 00 CLI |

Architecture review result remains `READY_FOR_USER_REVIEW; NOT APPROVED_FOR_IMPLEMENTATION`. This file does not change that.

---

## 1. Contradictions to resolve before code

These will produce conflicting implementations if left as-is. Precedence is PRD → evaluation strategy → accepted ADRs → LLD → phase plans.

### C-01 — Precision@K denominator

- **Strategy** (`docs/evaluation/evaluation-strategy.md` §3): `Precision@K = relevant identities in top K / K`, with documented behavior when fewer than K are returned.
- **LLD** (`docs/architecture/LLD.md` §7): denominator is actual returned count capped at K; zero returned yields `0.0` for an answerable case.
- **Lock (accepted):** Keep denominator **K** (standard IR; short lists are penalized). Empty retrieval for an answerable case scores `0.0`. No-answer cases do not use Precision@K.
- **Applied:** evaluation strategy §3 and LLD §7 now match.

### C-02 — Exit code 130

- **PRD FR-13:** `0 PASS`, `2 BLOCK`, `3 REVIEW_REQUIRED`, `4 invalid/non-comparable`, `5 infrastructure/internal failure`.
- **LLD §11 and Phase 00:** also `130 interrupted`.
- **Lock (accepted):** Add `130` to PRD FR-13 as the interrupted/SIGINT mapping. Keep `5` for internal/infrastructure failure after the process is still able to emit a result.
- **Applied:** PRD FR-13, LLD §11, HLD §5.

### C-03 — Case `ERROR` versus run comparability

- **Strategy §5:** `INVALID`/`ERROR` stay in the 50-case denominator; a non-comparable run cannot pass.
- **HLD §5:** `Invalid` and `Incomplete` are run statuses, not quality decisions. Only a comparable completed run can be `PASS` / `BLOCK` / `REVIEW_REQUIRED`.
- **Lock (accepted):**
  - Target timeout/rate-limit after bounded retries → case `ERROR`, run **completed**, quality decision allowed, floors apply (`ERROR` counts against pass rate).
  - Missing expected cases, process kill before finalize, corrupt/partial bundle → run **Incomplete**, exit `4` or `5` or `130`, no `PASS`/`BLOCK`/`REVIEW_REQUIRED`.
- **Applied:** evaluation strategy §5, HLD §5, LLD case-pass section.

### C-04 — “50 valid expected cases” versus case `INVALID`

- **Strategy §5** uses “passing cases divided by the 50 valid expected cases” and also says `INVALID` never leaves the denominator.
- **Lock (accepted):** Suite/config/schema failure aborts before scoring (`DATASET_INVALID` / `CONFIG_INVALID`, exit `4`). After a successful load, a per-case `INVALID` should be unreachable; if it occurs it is an internal defect (`5`) and the run is non-comparable.
- **Applied:** evaluation strategy §5, HLD §5, LLD.

### C-05 — Baseline signature versus hash

- **PRD / threat model:** signature or hash verification.
- **LLD `BaselineRecord`:** optional signature.
- **Lock (revised with G-27):** V1 identity is SHA-256 hash plus trusted base-branch/store resolution. Phase 07 waiver/promotion approval uses protected GitHub evidence. Cryptographic application signatures wait until Phase 08 selects an identity provider. Do not require signatures for local/CLI mode.
- **Applied for waivers:** evaluation strategy §11, Phase 07, LLD CLI note. Baseline-record optional-signature wording can wait for ADR-008 acceptance.

### C-06 — Compare during `run` versus separate `compare`

- **HLD sequence:** compare baseline before finalize.
- **LLD CLI:** both `run --baseline CHANNEL` and `compare --candidate --baseline`.
- **Phase 04:** runner without baseline or judge behavior.
- **Proposed lock:** Phase 04 `run` writes a bundle without `comparison.json` (exploratory / non-release). Phase 06 adds `run --baseline` (same compare service, writes `comparison.json`) and `compare`. Matches PRD FR-15.
- **Owning docs to patch:** HLD sequence note + Phase 04/06 cross-link. LLD CLI can stay as the completed contract.

### C-07 — Learning files “create” versus “update”

- Phase 09 says add `Learning/concepts/10-extension-profiles.md`; the file already exists.
- **Lock (accepted):** Later phases **update** existing Learning files. Do not create duplicates.
- **Applied:** Phase 09 Files section.

### C-08 — Phase 03 depends on `NormalizedOutcome` from Phase 02

- **Review finding:** Phase 03 currently depended only on Phase 01, but adapters must emit the Phase 02 `NormalizedOutcome` contract.
- **Lock (accepted):** Phase 03 depends on Phases 01 and 02.
- **Applied:** `Implementation.md` roadmap table and dependency diagram; Phase 03 prerequisites.

---

## 2. Spec gaps (underspecified; will be invented in code unless locked)

Close each gap in the owning document **before the named phase**, not by improvising in application code.

### Dataset and cases — before Phase 01

| ID | Missing item | Proposed lock | Owner |
|---|---|---|---|
| G-01 | 50-case inventory mapping IDs → behavior, tags, invariants, fixtures | Add section 5.1 using the coverage map in §4 of this file | `golden-dataset.md` |
| G-02 | Tag vocabulary | Closed enum in the suite manifest; unknown tags fail validation | `golden-dataset.md` |
| G-03 | Case ID pattern | `^(text\|safe\|struct\|rag\|tool)-\d{3}$` | `golden-dataset.md` |
| G-04 | Hard-invariant → case IDs | Every V1 hard invariant except integrity/baseline-substitution has at least one golden | `golden-dataset.md` |
| G-05 | Canonical hashing | UTF-8, LF, canonical JSON object key sort, SHA-256; suite hash over sorted `(relative_path, sha256)` excluding `checksums.json` itself | `golden-dataset.md` |
| G-06 | Unicode / whitespace policy | NFC; trim; collapse internal whitespace for normalized match; exact match remains raw | evaluation strategy §3 |
| G-07 | Regex policy | **Rejected as written** (`re` has no timeout). V1 allows only trusted repository-authored patterns in the golden suite; never compile target output or untrusted input; do not claim a timeout | evaluation strategy §3; applied |
| G-08 | JSON Schema dialect | Draft 2020-12 via `jsonschema` added in Phase 02; extra fields rejected when the referenced schema says so; domain stays free of the library | Phase 02 + strategy; applied |
| G-09 | Privacy classification enum | `synthetic-public` for `golden-v1` | `golden-dataset.md` |
| G-10 | Fixture license | Same as repository MIT `LICENSE`; restate in Phase 01 `REVIEW.md` | `LICENSE` added; `REVIEW.md` still Phase 01 |
| G-11 | Dataset owners / reviewers | Named roles even if placeholder identities | Phase 01 prerequisite |
| G-12 | Intended V1 targets | Fake adapter + local HTTP contract server; live providers opt-in | `golden-dataset.md` manifest |

### Metrics, judges, gates — before Phases 02 / 05 / 06

| ID | Missing item | Proposed lock | Before phase |
|---|---|---|---:|
| G-13 | nDCG formula | Discount `log2(rank+1)`; gain `2^rel - 1`; omit when labels are binary-only or ideal DCG is 0; duplicates collapsed to earliest rank | 02 |
| G-14 | p95 definition | Inclusive nearest-rank on sorted latencies; unavailable latencies cannot satisfy a required budget | 04/06 |
| G-15 | Cost formula and cost table schema | `sum(tokens_in * in_price + tokens_out * out_price)` from a versioned price table hashed into the run; missing prices → cost unavailable → review if cost gate required | 06 |
| G-16 | Weighted Cohen’s kappa | Linear weights on the ordinal scale | 05 |
| G-17 | Bootstrap LCB | Paired case resampling, 10_000 draws, recorded seed, percentile 95% lower bound on mean(candidate − baseline); no BCa in V1 | 06 |
| G-18 | Gate reason-code catalog | See §3 | 06 |
| G-19 | Rubric anchors and `[0,1]` map | Four rubrics only: relevance, faithfulness, completeness, citation-support; anchored ordinal 1–5 mapped to `{1:0.00, 2:0.25, 3:0.50, 4:0.75, 5:1.00}` | 05 |
| G-20 | Semantic pass/fail cut | Dimension fails if normalized score `< 0.75` (ordinal 4–5 pass) unless the case names a different cut in the suite; cut is data, not prompt | 05 |
| G-21 | Calibration slice | ≥20 adjudicated case-dimension labels; both pass/fail; ≥5 labels per gated rubric; freeze IDs in the calibration record | 05 |
| G-22 | Bias slices | V1 synthetic suite has no demographic slices. Apply the 10-point gap rule to **domain slices**: factual, injection, no-answer, citation. Document that demographic fairness is out of scope for `golden-v1` | 05 |

### Runtime / API / ops — before Phases 00 / 04 / 07 / 08

| ID | Missing item | Proposed lock | Before phase |
|---|---|---|---:|
| G-23 | Run ID format | ULID or UUID4 string; unique; existing ID fails publish | 04 |
| G-24 | Config JSON examples | One invalid-as-example file per required section: target, invocation, evaluators, judge, gate, artifacts, observability, privacy | 00/04 |
| G-25 | Secret-reference syntax | Environment variable names only in config (`api_key_env: "TARGET_API_KEY"`); never inline secrets | 00 |
| G-26 | Auth roles | `reader`, `runner`, `quality_owner`, `security_admin` | 08 |
| G-27 | Waiver approval | Protected GitHub approval evidence in Phase 07 (required reviewers / CODEOWNERS, GitHub actor on the waiver record). Cryptographic application signatures wait for Phase 08 IdP. No wildcard case scope; expiry ≤14 days | 07; applied |
| G-28 | Retention classes | `run-standard`, `online-short`, `quarantine-restricted` with TTLs chosen in Phase 08 | 08 |
| G-29 | Redaction catalog | Strip provider tokens, `Authorization` headers, secret canaries, and classified online payloads from logs, reports, and judge prompts | 03/08 |
| G-30 | Object-store / IdP product | Still postponed to Phase 08; LLD should name the **port** and env vars only | 08 |
| G-31 | Absolute latency SLO | Keep recommended case p95 `<=30s`, suite wall `<=12 min`, concurrency `<=5` until Phase 06 measures and versions a gate-policy change | 06 |
| G-32 | Default concurrency / retries | Concurrency 5; default attempts 1; max 3 only when adapter marks the request idempotent | 03/04 |

---

## 3. Proposed gate reason-code catalog

Failure taxonomy in the evaluation strategy stays as **case/finding codes**. Comparison decisions need a separate ordered reason list. Proposed V1 codes:

| Reason code | Typical decision | Waivable in V1? |
|---|---|---|
| `INTEGRITY_FAILURE` | BLOCK | No |
| `BASELINE_INCOMPATIBLE` | exit 4 / non-comparable | No |
| `BASELINE_UNTRUSTED` | BLOCK | No |
| `HARD_INVARIANT_SCHEMA` | BLOCK | No |
| `HARD_INVARIANT_FORBIDDEN_TOOL` | BLOCK | No |
| `HARD_INVARIANT_CITATION_IDENTITY` | BLOCK | No |
| `HARD_INVARIANT_EVIDENCE_BOUNDARY` | BLOCK | No |
| `HARD_INVARIANT_SECRET_DISCLOSURE` | BLOCK | No |
| `FLOOR_OVERALL` | BLOCK | No |
| `FLOOR_PROFILE` | BLOCK | No |
| `FLOOR_SAFETY` | BLOCK | No |
| `FLOOR_CONTRACT` | BLOCK | No |
| `REGRESSION_TOTAL_PASSED` | BLOCK | No |
| `REGRESSION_PROFILE_PASSED` | BLOCK | No |
| `REGRESSION_DETERMINISTIC_CASE` | BLOCK | No |
| `SEMANTIC_SAMPLE_INSUFFICIENT` | REVIEW_REQUIRED | Yes, if not a hard invariant |
| `SEMANTIC_LCB_FAIL` | BLOCK | No if calibrated and required |
| `SEMANTIC_INCONCLUSIVE` | REVIEW_REQUIRED | Yes |
| `JUDGE_UNAVAILABLE` | REVIEW_REQUIRED | Yes |
| `JUDGE_UNCALIBRATED` | REVIEW_REQUIRED | Yes |
| `BUDGET_LATENCY` | REVIEW_REQUIRED on PR; BLOCK on release if unresolved | Yes |
| `BUDGET_COST` | REVIEW_REQUIRED on PR; BLOCK on release if unresolved | Yes |
| `PROVENANCE_INCOMPLETE` | BLOCK | No |
| `RUN_INCOMPLETE` | exit 4/5, no quality decision | No |

Decision priority remains `BLOCK` over `REVIEW_REQUIRED` over `PASS`.

---

## 4. Proposed `golden-v1` coverage map

Use this as the Phase 01 case-authoring checklist. IDs may be reassigned if behaviors stay inside the locked 12/6/10/12/10 split and every hard invariant remains represented.

### Text / semantic — `text-001`–`text-012` (12)

| ID | Behavior |
|---|---|
| `text-001` | Exact fact match |
| `text-002` | Unicode / whitespace normalization |
| `text-003` | Multi-fact synthesis |
| `text-004` | Required concept present |
| `text-005` | Forbidden concept absent |
| `text-006` | Ambiguity: clarify or abstain |
| `text-007` | Concise versus verbose constraint |
| `text-008` | Numeric / unit normalization |
| `text-009` | Substring / regex expectation |
| `text-010` | Empty or too-short output fails |
| `text-011` | Conflicting instructions; deterministic expectation wins |
| `text-012` | Stable ordering of required values |

### Safety / abstention — `safe-001`–`safe-006` (6)

| ID | Behavior | Invariant? |
|---|---|---|
| `safe-001` | Missing evidence → `insufficient_evidence` | |
| `safe-002` | Prohibited disclosure / action | |
| `safe-003` | Prompt-injection resistance | |
| `safe-004` | Appropriate refusal | |
| `safe-005` | Secret canary must not appear | Yes — `SECRET_DISCLOSURE` |
| `safe-006` | False-refusal control (should answer) | |

### Structured output — `struct-001`–`struct-010` (10)

| ID | Behavior | Invariant? |
|---|---|---|
| `struct-001` | Nested valid document | |
| `struct-002` | Wrong type | |
| `struct-003` | Wrong enum | |
| `struct-004` | Extra field rejected | Yes — schema acceptance |
| `struct-005` | Missing required field | |
| `struct-006` | Numeric range | |
| `struct-007` | Business constraint assertion | |
| `struct-008` | Trailing prose forbidden | |
| `struct-009` | Malformed JSON | |
| `struct-010` | Array cardinality | |

### RAG — `rag-001`–`rag-012` (12)

| ID | Behavior | Invariant? |
|---|---|---|
| `rag-001` | Lexical retrieval hit | |
| `rag-002` | Semantic retrieval hit | |
| `rag-003` | Distractor resistance | |
| `rag-004` | Multi-document evidence | |
| `rag-005` | Graded labels for nDCG | |
| `rag-006` | Recall@K miss | |
| `rag-007` | Context truncation / evidence recall | |
| `rag-008` | Fabricated citation identity | Yes |
| `rag-009` | Citation completeness | |
| `rag-010` | No-answer | |
| `rag-011` | Cross-collection / tenant leak | Yes — evidence boundary |
| `rag-012` | Answerable with correct citation | |

### Tool use — `tool-001`–`tool-010` (10)

| ID | Behavior | Invariant? |
|---|---|---|
| `tool-001` | Correct tool selection | |
| `tool-002` | Exact arguments | |
| `tool-003` | Subset arguments | |
| `tool-004` | Order / partial order | |
| `tool-005` | Maximum steps | |
| `tool-006` | Repeated-loop detection | |
| `tool-007` | Recovery after a failed allowed call | |
| `tool-008` | Forbidden tool / action | Yes |
| `tool-009` | Wrong tool | |
| `tool-010` | Termination; no extra call | |

Integrity-hash failure and candidate baseline substitution are **run/CI** invariants, not golden cases.

### Proposed closed tag vocabulary

`factual`, `normalization`, `synthesis`, `ambiguity`, `refusal`, `injection`, `canary`, `schema`, `extra-fields`, `business-rule`, `lexical`, `semantic-retrieval`, `distractor`, `multi-document`, `citation`, `no-answer`, `isolation`, `tool-selection`, `tool-arguments`, `tool-order`, `termination`, `forbidden-action`.

---

## 5. Missing repo / process files

### Add before Phase 00 starts

| Item | Why | Status |
|---|---|---|
| Git repository on `main` | Run provenance requires git SHA and dirty flag | Done (`origin/main`) |
| `.gitignore` | Keep staging artifacts, `.env`, `__pycache__`, and session logs out | Done (tmux logs ignored) |
| `LICENSE` | Code and synthetic dataset | Done (MIT; `golden-v1` uses the same license) |
| Accepted `ADR-001` and `ADR-002` | Required before Phase 00 | Still required |
| ADR template | Date, owner, context, decision, consequences, superseded-by | Still open |

### Phase 00 already specifies (do not invent extra product)

`pyproject.toml` + lockfile, `.env.example`, `.dockerignore`, `Dockerfile`, `.github/workflows/ci.yml`, foundation package, unit tests for config/CLI/errors, Ruff/mypy/pytest.

### Useful additions not in phase files

| File | Why |
|---|---|
| `SECURITY.md` | Vulnerability reporting; matches threat model |
| `CONTRIBUTING.md` | One phase at a time; no paid tests by default |
| `CODEOWNERS` | Protect dataset, gate-policy, baseline paths |
| `CHANGELOG.md` | Product and schema versions |
| PR / issue templates | Dataset PRs must show ID diffs, profile counts, hash impact |

### Remove

`tmux-client-14112.log` — removed in `ad9512a` and ignored.

### Name consistency

On-disk files are `AGENTS.md` and `CLAUDE.md`. Keep that single spelling. A second `Agents.md` would break Linux CI on a case-sensitive filesystem.

---

## 6. Planned product artifacts (missing by design)

Do not pull these into an earlier phase.

| Phase | Create |
|---|---|
| 01 | `evaluation/datasets/golden-v1/{manifest.json,cases.jsonl,checksums.json,REVIEW.md,fixtures/}`, `evaluation/configs/validation.json`, loader/hash/validation |
| 02 | Evaluators, registry, hand-calculated metric fixtures |
| 03 | Fake + HTTP target adapters, attempt contract, retry policy |
| 04 | Runner, filesystem store, `run` / `replay` / `inspect`, reports, fake 50-case E2E |
| 05 | `evaluation/rubrics/*.json`, calibration records, fake/HTTP judge |
| 06 | `evaluation/configs/gate-policy-v1.json`, first baseline, `compare` / `promote-baseline`, bootstrap |
| 07 | Release workflow, waivers, gate attestation, candidate cannot write baselines |
| 08 | FastAPI wrapper, telemetry, object-store adapter, online sample/redaction/quarantine |
| 09 | E2E proof for 10+12+10 structured/RAG/tool cases on one runner |
| 10 | Operator/developer/CLI/API/runbooks, SBOM/scans, drills, release evidence index |

---

## 7. Learning and operations gaps

| Gap | Recommendation |
|---|---|
| Concept files are short outlines | Update in the phase that implements the concept; add worked numeric examples (Recall@K, kappa, 45/50 floor) |
| Eight production drills compressed into five scenario files | Add or expand scenarios for provider timeout / partial run, malformed judge JSON, cost/latency budget, and waiver expiry |
| No operator runbook besides `failure-triage.md` | Phase 10, as already planned |
| No CLI/API reference | Phase 10 |

---

## 8. Do not add in V1

These remain PRD non-goals. Reject review comments that introduce them.

- Dashboard SPA, SQL catalog, custom queue, MLflow, prompt IDE, model router
- Automatic goldens from production, automatic baseline promotion, automatic prompt rewrite
- Dynamic plugin marketplace or per-profile runners
- Judge-only safety, schema, tool, citation, or isolation gates
- Nightly 200+ suite as the PR gate
- Provider SDKs (HTTP + fake only)
- Paid-provider tests as default CI
- In-place mutation of published datasets, runs, or baselines

---

## 9. Remaining planning-only work

Applied 2026-09-10: C-01, C-02, C-03, C-04, C-07, C-08, G-07 (rejected/replaced), G-08, G-27, LICENSE, git/gitignore/tmux cleanup.

Still open before or during later phases (no application code yet):

1. Add the 50-case map, tag vocabulary, and hard-invariant case IDs to `golden-dataset.md` (G-01–G-04) before Phase 01.
2. Add the gate reason-code catalog beside the failure taxonomy (G-18) before Phase 06.
3. Lock nDCG, p95, cost, kappa weights, bootstrap LCB, Unicode, and hashing (G-05, G-06, G-13–G-17) in their owning phases.
4. Add example config / rubric / gate-policy JSON (G-24).
5. Accept or revise ADR-001 and ADR-002 as dated records before Phase 00.
6. Leave ADR-003–012 as candidates until their phases. C-05/C-06 remain documented; only the waiver-signature part of C-05 is applied.

---

## 10. Reviewer response template

Copy and fill:

```text
C-01 Precision@K: accept — divide by K
C-02 Exit 130: accept — added to PRD FR-13
C-03 ERROR vs Incomplete: accept — applied
C-04 INVALID denominator: accept — applied
C-05 Signature vs hash: revise — GitHub evidence in Phase 07; app signatures in Phase 08
C-06 run vs compare: not in this review pass
C-07 Learning create vs update: accept — Phase 09 updates existing file
C-08 Phase 03 depends on 02: accept — roadmap, diagram, Phase 03
G-07 Regex: reject as written — trusted repo patterns only; no re timeout
G-08 JSON Schema: accept with jsonschema in Phase 02
G-27 Waiver approval: revise — protected GitHub evidence in Phase 07

G-01..G-12 dataset gaps: accept-all / list revisions:
G-13..G-22 metric/judge/gate gaps: accept-all / list revisions:
G-23..G-32 runtime/API gaps: accept-all / list revisions:

Coverage map §4: accept / revise IDs — notes:
Reason codes §3: accept / revise — notes:
Process files §5: accept / drop (list):
Do-not-add §8: confirm / conflict with PRD:

Blockers before user approval of implementation:
Additional contradictions found in planning docs:
```
