# Interview Questions and Answers

## 1. Why evaluate GenAI with goldens instead of spot checks?

Goldens fix reviewed inputs and observable expectations, making candidate/baseline comparisons repeatable and failures attributable. Spot checks vary by reviewer and are easy to cherry-pick.

## 2. Why are deterministic evaluators first?

They are stable, cheap, auditable, and authoritative for exact contracts and safety invariants. A probabilistic judge adds no value to JSON validity, allowed tools, citation identity, or evidence isolation.

## 3. What can an LLM judge legitimately measure?

Narrow semantic dimensions such as relevance, faithfulness, completeness, or citation support when deterministic labels are insufficient. It needs anchored rubrics, strict output, versioning, calibration, repeatability checks, and human oversight.

## 4. Why is 50 cases both useful and insufficient?

It is small enough to curate and run on every release while broad enough for capability slices. One case moves pass rate by two points, so it cannot detect tiny effects or support broad population claims; larger separately governed suites are needed as domains expand.

## 5. Why use paired comparisons?

The same cases receive baseline and candidate outputs, so within-case deltas remove case-difficulty variation and reveal concrete pass→fail transitions.

## 6. Why can a candidate with the same pass count still block?

It may introduce a new deterministic failure, regress a primary profile, breach a hard invariant, or replace a previously passing critical case with an unrelated improvement.

## 7. What does `REVIEW_REQUIRED` mean?

The evidence is insufficient or inconclusive for an automatic quality claim. It blocks deployment until resolved or covered by a valid narrow non-hard waiver.

## 8. What does outcome replay prove?

Given the same normalized outcomes and compatible evaluator/gate versions, scoring and decisions reproduce. It does not prove an external provider will generate the same outcomes again.

## 9. Why not make MLflow or a database authoritative in V1?

Immutable self-describing run bundles already provide reproducibility, CI portability, and audit evidence. A catalog/tracker can index or import them later when collaboration/query scale justifies another dependency.

## 10. Explain Recall@K, MRR, and nDCG.

Recall@K measures how much labeled relevant evidence appears in the first K results. MRR rewards the rank of the first relevant result. nDCG rewards an ordering of graded relevance and is inappropriate without graded labels.

## 11. Distinguish citation validity, correctness, and completeness.

Validity means the citation identity is from approved context. Correctness means the evidence supports the associated claim. Completeness means all material factual claims that require evidence are cited.

## 12. How is tool use evaluated?

Separately score tool selection, version/allow-list, argument schema and values, ordering, maximum steps/loops, termination, and forbidden actions. A forbidden attempt is a hard failure even if the final text is good.

## 13. Why are online traces not goldens?

They lack reviewed labels, reflect biased changing traffic, and may contain sensitive data. Consent, redaction, quarantine, human labeling, and immutable dataset review are required first.

## 14. How do you prevent a pull request from grading itself?

Resolve baselines and gate policy from a protected base branch or trusted store, restrict candidate credentials to read-only, bind attestations to commit/run hashes, and separate promotion authority.

## 15. What should happen when a judge fails?

Preserve deterministic results and explicit judge failure evidence. Required semantic dimensions become review/non-comparable; never substitute a zero, reuse a stale hidden result, or pass silently.

## 16. Why write `COMPLETE` last?

Readers need one atomic publication signal that all files exist and hashes match. A crash before it leaves an ignorable staging/incomplete bundle.

## 17. How should thresholds change?

Through a versioned evaluation-policy change with measured baseline evidence, rationale, review, compatibility impact, and new tests—not an unexplained CI edit.

## 18. What is the most important triage rule?

Repair the first failing layer. Do not compensate for dataset, transport, retrieval, schema, or tool failures by tuning downstream prose.
