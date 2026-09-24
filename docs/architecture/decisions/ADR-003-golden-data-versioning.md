# ADR-003 — Golden data and versioning

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Phase 01 must produce exactly 50 reproducible, reviewable cases. Labels, fixtures, and expectations must be auditable and must never change under a published identity. `docs/evaluation/golden-dataset.md` fixes the directory and hashing contract; PRD FR-01/FR-02 and NFR reproducibility require strict parsing and content addressing.

## Decision

Store `golden-v1` as strict JSONL cases plus a JSON manifest, `checksums.json`, and reviewed synthetic fixtures. Identity is a SHA-256 content hash over a canonical sorted list of `(relative_path, sha256)` pairs excluding `checksums.json`. Published suite versions are immutable; any content, label, weight, or fixture change creates a new suite version. Schemas use Pydantic `extra="forbid"` discriminated by `primary_profile`, and no case contains executable YAML, templates, or code.

## Consequences

- Loaders can reject unknown fields and tampering before any target invocation.
- A run records both the human suite version and its content hash.
- Correcting a golden is a new version, not an in-place edit; historic runs stay addressable.
- JSONL plus JSON is portable and diff-reviewable but gives no cross-suite query without a later catalog.

## Alternatives considered

- Mutable spreadsheets: rejected — no content addressing or strict validation.
- Executable YAML/templates: rejected — untrusted data must never execute.
- Database-only labels: rejected — adds infrastructure before measured need and breaks offline use.

## Compliance

`validate` recomputes the suite hash and fails with exit `4` on any mismatch; tests assert exactly 50 IDs, the 12/6/10/12/10 distribution, profile-specific requirements, and traversal/oversize rejection.
