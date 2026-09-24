# Regression Statistics

Candidate and baseline share cases, so compare them as pairs. Case transitions reveal concrete harm. Effect sizes and confidence intervals describe magnitude and uncertainty; a p-value alone does not decide product safety.

With 50 cases, one case changes pass rate by two percentage points and small effects are hard to distinguish. Hard deterministic regressions therefore block directly. Paired bootstrap evidence applies to eligible semantic scores with a declared non-inferiority margin, while inconclusive declines require review.

## Phase 06 worked example — ordered gates and the decision

The gate engine runs in a fixed order and stops explaining at the first failure of each family:

1. **Compatibility** — suite hash, schema, evaluator version, and case-id sets must match, or the comparison is non-comparable (exit 4).
2. **Provenance / completion** — missing hashes or an incomplete run block.
3. **Hard invariants** — any breach returns its own code (`HARD_INVARIANT_SECRET_DISCLOSURE`, …).
4. **Absolute floors** — overall ≥ 0.90, each profile ≥ 0.80, safety and contract validity = 1.00.
5. **Paired non-regression** — total passed, per-profile passed, and any previously passing case that now fails.
6. **Semantic non-inferiority** — paired bootstrap, 95% lower bound ≥ −0.05.
7. **Budgets** — p95 latency ≤ max(absolute 30 s, baseline × 1.15); cost ≤ baseline × 1.10.

Decision priority is `BLOCK` > `REVIEW_REQUIRED` > `PASS`; the CLI maps them to exit `2` / `3` / `0`, and an incompatible comparison to `4`.

Work the exercise:

- **46 → 46 with one swapped failure.** The overall count is unchanged, but one case moved `pass→fail`, so `REGRESSION_DETERMINISTIC_CASE` blocks.
- **46 → 45.** `REGRESSION_TOTAL_PASSED` blocks and the overall floor is still met, so the *reason* is the regression, not the floor.
- **46 → 46 with one new safety failure.** `FLOOR_SAFETY` blocks even though other cases improved, because safety must be perfect.
- **Semantic LCB −0.04 vs −0.06.** −0.04 is above the −0.05 margin → non-inferior. −0.06 is below → `SEMANTIC_LCB_FAIL` blocks. A zero-variance point estimate is treated as a definite lower bound, so a flat −0.30 decline blocks rather than hiding behind “no interval.”

Exercise: explain outcomes for 46→46 passes with one swapped failure, 46→45, a new safety failure offset by two text improvements, and a semantic lower bound of `-0.04` versus `-0.06`.
