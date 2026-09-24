# ADR-009 — HTTP/service scope

**Status:** ACCEPTED (identity provider and object store selected at deployment)  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Phase 08 exposes the existing application services over HTTP for read-mostly access and protected mutations. The API must not duplicate evaluation, gate, or persistence logic, and V1 must not add a bespoke queue or dashboard.

## Decision

Add a thin FastAPI wrapper (`api.py`) whose routes translate HTTP to the same `RunService` / `CompareService` / `PromotionService` calls the CLI uses. Authentication is Bearer-token OIDC/JWT validated by an injectable verifier; roles are `reader`, `runner`, `quality_owner`, `security_admin`, and the server derives the actor/tenant from the token, never from the request body. `POST /v1/runs` is idempotent by key. Errors use `{error: {code, message, retryable, correlation_id, details}}`. Defaults pending deployment: HS256 JWT with a shared secret (via env) for local/CI, and a local object store; the real OIDC issuer/JWKS and object store are selected at deployment.

## Consequences

- CLI and API share one core; a route test proves identical application results.
- No self-hosted queue: long runs reuse the platform job runner if needed.
- Auth, e-mail/JWKS rotation, and object-store choice remain deployment tasks.

## Alternatives considered

- Separate API evaluator: rejected — two sources of truth.
- Anonymous service: rejected — promotions and quarantine need authorization.
- Dashboard SPA / custom queue: rejected in V1 (PRD non-goals).

## Compliance

`tests/unit/test_api.py` proves route/service parity and error mapping; `tests/unit/test_auth.py` covers role and tenant boundaries; CI runs them without network.
