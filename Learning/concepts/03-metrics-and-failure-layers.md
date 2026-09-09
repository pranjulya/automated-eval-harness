# Metrics and Failure Layers

Metric choice follows the question. Recall@K asks whether needed evidence was retrieved; MRR asks how early the first relevant result appears; nDCG needs graded relevance. Structured validity asks whether a contract holds. Tool evaluation separates selection, arguments, order, and termination. No-answer evaluation needs both false answers and false refusals.

The first failing layer is usually the best repair location. If retrieval misses evidence, changing the generation prompt treats a symptom. If a tool is forbidden, a fluent final answer does not make the run safe. Aggregate pass rate is useful only beside profiles, tags, case transitions, and hard invariants.

Exercise: hand-calculate the documented metrics for a five-result ranking containing duplicates and two graded relevant items.
