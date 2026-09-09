# CI Gates and Waivers

The candidate must not choose its examiner. CI resolves the baseline and gate policy from a protected source, binds the decision to the exact commit/run hashes, and makes deployment depend on a verified `PASS` attestation.

A waiver is visible risk acceptance, not a hidden skip. It is narrow, approved, owned, time-bounded, and cannot cover hard invariants. `REVIEW_REQUIRED` blocks because uncertainty is not evidence of quality.

Exercise: threat-model a pull request that edits the baseline, workflow, expected case count, artifact, or waiver and show which protected boundary rejects it.
