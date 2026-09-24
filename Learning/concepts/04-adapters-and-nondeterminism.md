# Adapters and Nondeterminism

An adapter translates transport/provider details into one normalized outcome. It records model/config evidence but does not decide quality. Separating transport states from semantic results prevents timeouts, malformed data, and wrong answers from becoming one vague failure.

Retries are safe only when the operation and failure point make repetition safe. Record every attempt. A stable seed and temperature zero can reduce variation but do not guarantee identical external inference; provider aliases, infrastructure, and hidden model changes still matter.

## Phase 03 worked example — one contract, two transports

The fake adapter and the HTTP adapter must produce byte-identical `NormalizedOutcome` values for the same case. The contract test runs all 50 fake responses through both; any divergence in status, text, structured value, evidence, citations, tool trace, or usage fails the build. That test is what makes replay and baseline comparison transport-independent.

Retry decisions are explicit and conservative:

| Failure | Retried? | Why |
|---|---|---|
| Connection refused / transport error | Yes, if idempotent | Request never reached the target. |
| `429` rate limited | Yes, if idempotent | Safe to repeat after backoff. |
| Read timeout after acceptance | Yes, if idempotent | May duplicate work, so only declared-idempotent operations. |
| `5xx` target error | Only if the adapter marks it idempotent | Could be a real server fault. |
| Schema-invalid / malformed output | No | Repeating cannot fix a contract violation. |
| Forbidden tool selection | No | It is a safety finding, not a transport glitch. |

Every attempt is preserved with its own request hash, status, usage, and latency; the final outcome is the last attempt. Default is one attempt, the hard maximum is three, backoff doubles and is capped, and a `KeyboardInterrupt` propagates immediately.

Nondeterminism is recorded honestly: if a provider exposes only a model alias, the identity sets `externally_nondeterministic=true` instead of pretending the run is reproducible.

Exercise: decide retry behavior for connection refusal, 429, read timeout after request acceptance, schema-invalid output, and forbidden tool selection. Then explain why the fake target's request hash still matters even though the fake never touches a network.
