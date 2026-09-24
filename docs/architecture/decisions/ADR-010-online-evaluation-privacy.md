# ADR-010 — Online evaluation and privacy

**Status:** ACCEPTED (retention/consent values set at deployment)  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Online signals may reveal drift but must never silently rewrite offline truth. Production content is sensitive by default and needs consent, redaction, quarantine, retention, and human review.

## Decision

Online sampling is opt-in and policy-scoped. Candidates are redacted before persistence, stored in quarantine, and advanced only by explicit human review. Online signals may raise alerts and propose a redacted draft case, but can never publish datasets, rubrics, thresholds, or baselines. Retention classes (`run-standard`, `online-short`, `quarantine-restricted`) carry TTLs; deletion is authorized and recorded as evidence. Defaults: `online-short` TTL = 7 days, `quarantine-restricted` TTL = 30 days, consent required, redaction catalog = provider tokens / `Authorization` headers / secret canaries / classified payloads.

## Consequences

- Production content never reaches a golden suite without human promotion.
- Quarantine access is restricted to `quality_owner`/`security_admin`.
- TTLs and consent policy are deployment inputs, not code constants.

## Alternatives considered

- Ingest all traces: rejected — privacy and noise.
- Auto-golden / auto-baseline: rejected — violates offline authority.

## Compliance

`tests/unit/test_online_samples.py` covers consent, redaction, quarantine, retention expiry, deletion evidence, and the no-auto-promotion rule.
