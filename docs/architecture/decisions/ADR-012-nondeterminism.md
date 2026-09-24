# ADR-012 — Nondeterminism

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

External providers may not expose stable model versions or deterministic inference. Baselines and semantic comparisons must not pretend otherwise, and replay must stay reliable.

## Decision

Record version capability honestly; when a provider is marked `externally_nondeterministic`, release runs use three replicates and aggregate a case by majority for pass/fail and median for numeric scores/latency, retaining every attempt. Replay re-scores recorded normalized outcomes deterministically and never claims provider determinism. Seeds are recorded where supported but are not treated as a guarantee.

## Consequences

- Release runs cost more for nondeterministic targets but report honest uncertainty.
- Aggregate functions must be explicit (`majority`, `median`) and tested.
- A run whose provider lost a stable version is not silently compared as if deterministic.

## Alternatives considered

- Treat temperature 0 as deterministic: rejected — provider internals still vary.
- Single run for all targets: rejected for nondeterministic providers.

## Compliance

`tests/unit/test_statistics.py` covers majority/median aggregation and seeded bootstrap reproducibility; the manifest records the nondeterminism declaration.
