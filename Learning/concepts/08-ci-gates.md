# CI Gates and Waivers

The candidate must not choose its examiner. CI resolves the baseline and gate policy from a protected source, binds the decision to the exact commit/run hashes, and makes deployment depend on a verified `PASS` attestation.

A waiver is visible risk acceptance, not a hidden skip. It is narrow, approved, owned, time-bounded, and cannot cover hard invariants. `REVIEW_REQUIRED` blocks because uncertainty is not evidence of quality.

## Phase 07 worked example — attestation and the deploy boundary

The release workflow runs the approved 50-case suite, compares it to the trusted baseline, and writes a `GateAttestation` that binds:

- the **commit** under test,
- the **run-manifest hash** (so a different run cannot be substituted),
- the **baseline record hash** (so the comparison target is fixed),
- the **workflow identity**, **decision**, **reason codes**, and a **timestamp/TTL** (default 24 h).

The `deploy` job declares `needs: gate` and `if: needs.gate.outputs.decision == 'PASS'`, so `BLOCK` and `REVIEW_REQUIRED` skip deployment entirely. Even on the `PASS` path the job re-verifies the attestation with `verify-attestation --commit $GITHUB_SHA`, so a stale or tampered artifact cannot authorize a deploy.

Trust boundaries in this design:

- **Baseline** comes from a trusted store (default: an artifact produced only by the protected promotion workflow; upgrade path: object store in Phase 08). If no baseline is present, the gate fails closed with `BASELINE_UNTRUSTED` rather than inventing one.
- **Promotion** is a separate `workflow_dispatch` job in a protected environment with required reviewers, using different authority from candidate execution. A candidate cannot promote itself.
- **Waivers** require a GitHub approver identity with evidence, exact suite/channel/reason/case scope, a compensating control, and expiry ≤ 14 days. `*` scope and any hard-invariant reason are rejected. An accepted waiver suppresses only its eligible reason codes and is recorded on the comparison.

Exercise: threat-model a pull request that edits the baseline, workflow, expected case count, artifact, or waiver and show which protected boundary rejects it.
