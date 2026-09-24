# Metrics and Failure Layers

Metric choice follows the question. Recall@K asks whether needed evidence was retrieved; MRR asks how early the first relevant result appears; nDCG needs graded relevance. Structured validity asks whether a contract holds. Tool evaluation separates selection, arguments, order, and termination. No-answer evaluation needs both false answers and false refusals.

The first failing layer is usually the best repair location. If retrieval misses evidence, changing the generation prompt treats a symptom. If a tool is forbidden, a fluent final answer does not make the run safe. Aggregate pass rate is useful only beside profiles, tags, case transitions, and hard invariants.

## Phase 02 worked example — hand calculation

Take `retrieved = [d1, d2, d2, d3, d4]`, relevant `{d1, d3}`, graded `{d1: 2, d3: 1}`, `K = 3`.

Duplicates collapse to the earliest rank, so the ranking becomes `[d1, d2, d3, d4]`.

- `Recall@3 = |{d1, d3}| / 2 = 1.0` (both relevant identities are in the top 3).
- `Precision@3 = 2 / 3 = 0.667` — always divide by **K**, not by the number returned. A one-result list with one relevant hit scores `1/3`, which is why short lists are penalized.
- `MRR = 1 / 1 = 1.0` (the first result is relevant).
- `nDCG@3` with gain `2^rel − 1` and discount `log2(rank + 1)`:
  - observed gains `[3, 0, 1]` → `3/1 + 0/1.585 + 1/2 = 3.5`
  - ideal gains `[3, 1]` → `3/1 + 1/1.585 = 3.631`
  - `nDCG@3 = 3.5 / 3.631 = 0.964`

Contrast with a tempting wrong answer: using `log2(rank)` instead of `log2(rank + 1)`, or dividing Precision@K by the returned count, both change the number and would silently change a gate later.

## Failure layers and case state

Findings carry a severity and a stable code. Case state follows fixed precedence: no usable outcome → `ERROR`; any failing hard invariant or deterministic finding → `FAIL`; required semantic evidence unavailable → `REVIEW_REQUIRED`; otherwise `PASS`. A hard invariant outranks a semantic review, so a canary disclosure can never be downgraded to “needs review.”

`INVALID` is a **run** status for dataset/config failure, never a case result. A per-case invalid after a successful load is an internal defect.

Exercise: hand-calculate the documented metrics for a five-result ranking containing duplicates and two graded relevant items, then state which finding would fire first if the forbidden tool `delete_account` were called in a RAG case.
