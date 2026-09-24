# golden-v1 Review Record

**Suite:** `golden-v1` 1.0.1  
**Schema:** `eval.case.v1`  
**Content hash:** computed and stored in `manifest.json`; recomputed by `validate`.  
**Privacy classification:** `synthetic-public`  
**License:** MIT (repository `LICENSE`), applies to all synthetic cases and fixtures.

## Distribution

| Profile | Cases | IDs |
|---|---:|---|
| text/semantic | 12 | `text-001`–`text-012` |
| safety/abstention | 6 | `safe-001`–`safe-006` |
| structured output | 10 | `struct-001`–`struct-010` |
| RAG | 12 | `rag-001`–`rag-012` |
| tool use | 10 | `tool-001`–`tool-010` |
| **Total** | **50** | |

## Hard-invariant coverage

| Invariant | Case(s) |
|---|---|
| Schema acceptance (extra field rejected) | `struct-004` |
| Forbidden tool / action | `tool-008` |
| Citation identity | `rag-008` |
| Evidence boundary (cross-tenant) | `rag-011` |
| Secret canary disclosure | `safe-005` |
| Integrity hash / baseline substitution | run/CI invariants, not golden cases |

## Review evidence

- Author: `project-team`.
- Reviewers: `domain-reviewer`, `eval-reviewer` (placeholder identities recorded per G-11).
- Deterministic labels are hand-specified in the case files; no label was inferred from a model.
- All cases are synthetic; no production record was used.
- Fixtures contain only fabricated strings (for example `CANARY-7f3a9`, `ALPHA-ONLY`); none is a real secret.
- Disagreements: none recorded at authoring time.

## Change control

Published suites are immutable. To correct a case, publish a new `suite_version`, update
`manifest.json` and `checksums.json`, and record the reason here. Historic runs remain
readable under their original content hash.

- **1.0.1 (2026-09-10):** corrected `struct-004`. Its JSON Pointer assertion required
  `/order` to have length 3 while the referenced schema requires five fields. Replaced the
  assertion with `/order/id` existence; extra-field rejection is enforced by the schema's
  `additionalProperties: false` under the `HARD_INVARIANT_SCHEMA` check. No other case changed.
