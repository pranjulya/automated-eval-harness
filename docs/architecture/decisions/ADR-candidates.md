# Architecture Decision Candidates

**Status:** RECOMMENDED; accept the listed ADR before its owning phase begins.  
**Rule:** acceptance records date, owner, context, decision, consequences, and superseded decision. Do not silently reinterpret a candidate in code.

| ADR | Decision | Recommendation | Alternatives rejected/deferred | Required before |
|---|---|---|---|---:|
| ADR-001 | Runtime and packaging | Python 3.12+, `src/` package, Pydantic v2, pytest/Ruff/mypy | polyglot runtime; framework-heavy scaffold | 00 — ACCEPTED 2026-09-10 (`ADR-001-runtime-and-packaging.md`) |
| ADR-002 | User entry point | standard-library `argparse` CLI is authoritative; FastAPI later wraps services | Typer/Click dependency; API-first; notebook authority | 00 — ACCEPTED 2026-09-10 (`ADR-002-cli-entry-point.md`) |
| ADR-003 | Golden data/versioning | strict JSONL cases + JSON manifest/checksums, SHA-256 identity, immutable versions | mutable spreadsheets; executable YAML/templates; database-only labels | 01 |
| ADR-004 | Scoring model | deterministic hard/contract/profile evaluators first; explicit profile registry; `jsonschema` Draft 2020-12 in the structured evaluator | one opaque composite score; judge-only evaluation; ad-hoc JSON parsers | 02 |
| ADR-005 | Persistence/experiments | immutable run bundles on filesystem/object store; no SQL or hosted tracker required | PostgreSQL/MLflow from day one | 04 |
| ADR-006 | Semantic judging | rubric-specific, structured, calibrated judge with human agreement thresholds | “is this good?” judge; majority of uncalibrated judges | 05 |
| ADR-007 | Regression policy | absolute floors + paired case non-regression + paired bootstrap non-inferiority; `REVIEW_REQUIRED` blocks deploy | aggregate-only threshold; p-value-only decision | 06 |
| ADR-008 | CI and waivers | trusted base-branch baseline, stable exit codes, immutable artifacts, scoped expiring waiver with protected GitHub approval evidence; hard invariants non-waivable | candidate-owned baseline; permanent ignore list; app signatures before an IdP exists | 07 |
| ADR-009 | HTTP/service scope | read-mostly FastAPI wrapper and protected promotions; platform job runner if needed | custom distributed queue/dashboard SPA | 08 |
| ADR-010 | Online evaluation/privacy | opt-in sampling, redact before persist, quarantine, human promotion only | ingest all traces; auto-golden/auto-baseline | 08 |
| ADR-011 | Extension boundary | first-party discriminated profiles reuse one runner/result/gate lifecycle | dynamic plugin marketplace; profile-specific runners | 09 |
| ADR-012 | Nondeterminism | record capability, three release replicates when needed, majority/median aggregation, deterministic replay of outcomes | pretending temperature zero is deterministic | 06 |

## Consequences to make explicit

- Artifact-first persistence gives simple auditability and CI portability but limited cross-run querying. Add a SQL/catalog index only after measured discovery or concurrency pain; artifacts remain authoritative.
- `argparse` avoids a dependency and keeps stable exit behavior, but help/output needs deliberate tests.
- Fifty cases are a release contract, not a statistically representative universe. A larger separately governed suite is the upgrade path.
- A three-state gate is more honest than coercing uncertain evidence into pass/fail; CI treats uncertainty as deploy-blocking.
- Judge calibration costs human review time. That cost is required before semantic scores carry release authority.
- Online sampling improves drift discovery but creates privacy obligations; it stays isolated from immutable offline truth.

## Decisions deliberately postponed

- Exact dependency patch versions: select and lock during Phase 00 using supported releases at that time.
- Specific target/judge provider: adapters and configs are provider-neutral; choose only for an approved deployment.
- Shared object-store product and identity provider: select in Phase 08 for the deployment environment.
- SQL catalog, web dashboard, distributed workers, scheduled nightly suite, and external experiment tracker: add only after observed scale/collaboration demand and a new ADR.
