# CLI and HTTP API Reference

The CLI is authoritative; the HTTP API wraps the same application services.

## Exit codes

`0` success/PASS · `2` BLOCK · `3` REVIEW_REQUIRED · `4` invalid/non-comparable · `5` infrastructure/internal · `130` interrupted.

## CLI

```bash
eval-harness validate   --suite PATH --config PATH [--format text|json]
eval-harness run        --suite PATH --config PATH [--case ID ...] [--profile NAME] [--tag TAG] [--run-id ID] [--format text|json]
eval-harness replay     --run RUN_ID
eval-harness inspect    --run RUN_ID [--failures-only] [--format text|json]
eval-harness compare    --candidate RUN_ID --baseline CHANNEL --suite NAME [--policy PATH] [--waiver FILE ...] [--format text|json]
eval-harness promote-baseline --run RUN_ID --suite NAME --channel NAME --reason TEXT --approval-file PATH [--policy PATH]
eval-harness verify-attestation --file PATH [--commit SHA] [--run-manifest-hash H] [--baseline-hash H] [--allow-expired]
eval-harness --version | --help
```

Environment: `EVAL_HARNESS_ENVIRONMENT`, `EVAL_HARNESS_LOG_LEVEL`, `EVAL_HARNESS_ARTIFACT_ROOT`, `EVAL_HARNESS_SECRET_REFS`. Secrets are referenced by environment-variable name only.

## HTTP API

Bearer token required unless noted. Errors: `{"error": {"code", "message", "retryable", "correlation_id", "details"}}`.

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/health/live` | – | liveness |
| GET | `/health/ready` | – | artifact-store readiness |
| POST | `/v1/runs` | runner | idempotent via `Idempotency-Key`; returns `202` |
| GET | `/v1/runs/{run_id}` | reader | manifest + summary |
| GET | `/v1/runs/{run_id}/cases` | reader | `?profile=&state=` |
| POST | `/v1/comparisons` | reader | `{candidate_run_id, suite, channel}` |
| GET | `/v1/baselines/{suite}/{channel}` | reader | immutable record |
| POST | `/v1/baselines/{suite}/{channel}/promotions` | quality_owner | server-derived actor |
| GET | `/v1/samples` | quality_owner/security_admin | quarantined samples |
| POST | `/v1/samples` | runner | consent required |
| POST | `/v1/samples/{id}/review` | quality_owner | accept/reject |
| GET | `/v1/samples/{id}/draft` | quality_owner | redacted draft only |
| DELETE | `/v1/samples/{id}` | security_admin | returns deletion evidence |

Roles: `reader`, `runner`, `quality_owner`, `security_admin`. The server derives actor and tenant from the verified token, never from the request body.
