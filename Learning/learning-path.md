# Learning Path

## Stage 1 — Define quality before tools

Read the PRD and HLD. Write the product promise and five non-goals from memory. Draw the trust boundaries and identify which component owns scoring, transport, persistence, and deploy authorization.

Checkpoint: explain why “the answer looks good” and “the provider returned 200” are not release criteria.

## Stage 2 — Build trustworthy goldens

Study concepts 01–02 with Phases 00–01. Hand-author one case per profile, calculate the suite hash inputs, and review each for observable expectations, privacy, ambiguity, and overfitting.

Checkpoint: explain why a corrected label needs a new dataset version and why production traces are not automatically truth.

## Stage 3 — Separate deterministic layers

Study concept 03 with Phase 02. Calculate Recall@K, MRR, nDCG, a no-answer confusion matrix, a structured assertion, and a tool partial-order result by hand. Classify a failing answer by its first failing layer.

Checkpoint: explain why a correct final sentence cannot compensate for a forbidden tool call or fabricated citation.

## Stage 4 — Control invocation and uncertainty

Study concept 04 with Phase 03. Draw timelines for success, timeout before response, rate limit, malformed response, and safe/unsafe retry. Identify what a provider/model alias cannot prove.

Checkpoint: distinguish transport retryability, target correctness, and statistical nondeterminism.

## Stage 5 — Make evidence reproducible

Study concept 05 with Phase 04. Trace one case from dataset hash through attempts, findings, summary, report, and `COMPLETE` marker. Kill a write in the thought experiment and explain why readers ignore it.

Checkpoint: explain how replay proves evaluator reproducibility without proving provider reproducibility.

## Stage 6 — Calibrate semantic judgment

Study concept 06 with Phase 05. Score a frozen slice as a human, adjudicate disagreement, calculate pass/fail agreement and kappa, and test a judge prompt-injection example.

Checkpoint: explain why a judge is a measurement instrument that needs calibration, not ground truth.

## Stage 7 — Gate regressions honestly

Study concepts 07–08 with Phases 06–07. Walk the 45/50 floor, a pass→fail transition, a profile regression, an inconclusive semantic interval, latency/cost increase, and waiver eligibility.

Checkpoint: explain why `REVIEW_REQUIRED` blocks deployment and why 50 cases cannot prove a tiny improvement.

## Stage 8 — Operate without leaking data

Study concept 09 with Phase 08. Trace an online sample through consent, redaction, quarantine, retention, human review, and deletion. Design bounded metrics without case/user identifiers.

Checkpoint: distinguish logs, metrics, traces, immutable run evidence, and sensitive quarantined artifacts.

## Stage 9 — Prove extension boundaries

Study concept 10 with Phase 09. Walk structured, RAG, and tool cases through the same runner. Identify profile-specific data and shared lifecycle components.

Checkpoint: explain citation validity/correctness/completeness and tool selection/arguments/order/termination as distinct dimensions.

## Stage 10 — Defend the production design

Run every scenario and answer the interview set. Present one candidate release in ten minutes: manifest, case deltas, hard invariants, semantic uncertainty, cost/latency, decision, artifacts, and remediation.

Final checkpoint: defend no SQL database, dashboard SPA, dynamic plugin loader, automatic golden creation, or judge-only gating in V1—and name the evidence that would justify each later.
