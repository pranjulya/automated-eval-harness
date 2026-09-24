# Extension Profiles

Profiles differ in observable evidence, not lifecycle. Structured output adds parsed values/schema assertions. RAG adds ranked evidence, claims, citations, and no-answer. Tool use adds a trace of names, arguments, order, and termination. All still validate, invoke, score, aggregate, compare, and persist through one runner.

Citation validity asks whether the ID is approved; correctness asks whether evidence supports the claim; completeness asks whether material claims are cited. Tool correctness likewise separates selection, arguments, order, and safety. Keeping dimensions separate makes failures repairable.

## Phase 09 worked example — 32 cases, one lifecycle

All 10 structured, 12 RAG, and 10 tool-use goldens run through the same `RunService`, write the same bundle, replay from the same `outcomes.jsonl`, and gate through the same engine as the text and safety profiles. The E2E test asserts each failure mode is attributed to a stable code:

| Profile | Failure | Code | Severity |
|---|---|---|---|
| structured | wrong type / enum / extra / missing field | `HARD_INVARIANT_SCHEMA` | hard invariant |
| structured | range / cardinality | `BUSINESS_ASSERTION_FAILED` | deterministic |
| RAG | relevant evidence not retrieved | `RETRIEVAL_MISS` | deterministic |
| RAG | required evidence lost from context | `CONTEXT_EVIDENCE_LOST` | deterministic |
| RAG | citation missing | `CITATION_INCOMPLETE` | deterministic |
| RAG | answer to an unanswerable case | `NO_ANSWER_FALSE_POSITIVE` | deterministic |
| RAG | citation of unknown evidence | `HARD_INVARIANT_CITATION_IDENTITY` | hard invariant |
| RAG | cross-tenant evidence | `HARD_INVARIANT_EVIDENCE_BOUNDARY` | hard invariant |
| tool | wrong arguments | `TOOL_ARGUMENT_FAILED` | deterministic |
| tool | repeated / too many calls | `TOOL_LOOP` | deterministic |
| tool | call after termination | `TOOL_SELECTION_FAILED` | deterministic |
| tool | forbidden tool | `HARD_INVARIANT_FORBIDDEN_TOOL` | hard invariant |

Diagnostics (Recall@K, MRR, nDCG) appear as `INFO` findings and are averaged in the report's **Profile diagnostics** section. The gate engine ignores `INFO`, so a diagnostic can never change a decision — only a real finding can.

Exercise: add a conceptual classification profile by naming only its expectation, normalized evidence, deterministic evaluator, report projection, and tests—without inventing a plugin loader or second runner.
