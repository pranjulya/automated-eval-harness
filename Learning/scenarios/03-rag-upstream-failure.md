# Scenario 03 — Fluent RAG Answer, Missing Evidence

## Situation

A retriever change removes the relevant evidence from top 10 for one answerable case. The generator still produces the correct reference fact from model memory and cites a different retrieved page.

## Expected evaluation

Retrieval records `RETRIEVAL_MISS`; the unsupported claim and citation are diagnosed separately. The newly failing deterministic case returns `BLOCK`. A high semantic relevance score cannot repair the missing evidence.

## Triage

Owner starts with retrieval/index configuration, not the generation prompt. Compare ranked evidence identities, context trimming, and changed retrieval variables. After retrieval is repaired, re-run downstream grounding/citation checks.

## Questions

Why score retrieval before generation? Distinguish citation validity, correctness, and completeness. What would cross-collection evidence change about severity?
