# Service Runbook (Phase 08)

**Status:** default wiring; deployment selections pending.

## Local / CI defaults

- Identity: HS256 JWT with a shared secret. Set `EVAL_HARNESS_JWT_SECRET` (≥32 bytes).
  Real deployments select an OIDC issuer/JWKS and replace `HmacJwtVerifier`.
- Object store: `LocalObjectStore` (filesystem-backed, content-addressed). The
  production S3/GCS adapter implements the same immutable-object contract.
- Artifacts: `EVAL_HARNESS_ARTIFACT_ROOT` (default `./artifacts`).
- Online samples: in-memory store for local/CI; production swaps in a durable
  store. Default TTLs: `online-short` 7 days, `quarantine-restricted` 30 days.

## Roles

| Role | Can do |
|---|---|
| `reader` | read runs, comparisons, baselines |
| `runner` | create runs, submit samples |
| `quality_owner` | review samples, propose drafts, promote baselines |
| `security_admin` | delete quarantined samples, promotion |

## Routine operations

1. **Run evaluation:** `POST /v1/runs` (idempotent via `Idempotency-Key`) or the CLI.
2. **Compare:** `POST /v1/comparisons` with candidate run + suite/channel.
3. **Promote baseline:** protected `quality_owner` action with approval evidence.
4. **Review samples:** list, review, propose a draft; never auto-publish.
5. **Delete a sample:** `security_admin` only; returns deletion evidence.
6. **Retention:** call `purge_expired` on a schedule; it removes expired samples.

## Incident procedures

- **Provider/judge outage:** jobs degrade to `REVIEW_REQUIRED`; no deploy.
- **Telemetry collector outage:** evaluation decisions are unaffected; metrics buffer locally and drop, never corrupt scoring.
- **Object-store outage/corruption:** readiness reports `degraded`; integrity-checked reads refuse corrupt bundles.
- **Redaction failure or PII detected:** quarantine the sample, restrict access, then delete with evidence.
- **Emergency release:** requires a valid `PASS` attestation for the exact commit; unverified attestations are refused.

## Health

- `GET /health/live` — process liveness.
- `GET /health/ready` — artifact-store reachability (`artifacts: true|false`).
