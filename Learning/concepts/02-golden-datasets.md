# Golden Datasets

A golden case is a reviewed claim about observable expected behavior. It is not merely a captured request/response. Good goldens cover meaningful risk and capability slices, contain sufficient evidence, state ambiguity, and use deterministic assertions wherever possible.

Version data and labels immutably because changing a case changes the measuring instrument. A comparison across different goldens may be interesting, but it is not a paired regression. Synthetic V1 data reduces privacy and licensing risk; real data needs consent, redaction, access, and retention controls.

## Phase 01 worked example — content addressing and the self-reference trap

`golden-v1` has 50 strict JSONL cases, a `manifest.json`, a `checksums.json`, and reviewed fixtures. Identity is a SHA-256 hash over a canonical sorted list of `(relative_path, sha256)` pairs.

The subtle part is that `manifest.json` declares `content_hash`, yet `manifest.json` is itself part of the suite. Hashing the file verbatim would be circular: writing the hash changes the file, which changes the hash. The harness breaks the cycle by canonicalizing `manifest.json` **with its own `content_hash` field removed** before hashing. Verification repeats the same normalization, so the declared hash is reproducible and still sensitive to every other manifest field (owners, counts, versions).

Two failure modes this design catches before any model is called:

- **Tampering:** changing `cases.jsonl` breaks both its entry in `checksums.json` and the suite hash.
- **Coverage gaps:** adding a file that `checksums.json` does not list fails validation, so an attacker cannot smuggle an extra fixture into the measured inputs.

Why this matters for regression claims: a candidate and its baseline are only paired if their suite identity matches. Comparing across a silently edited suite would hide a measurement change as a quality change.

Exercise: review five proposed cases for ambiguous wording, hidden implementation assumptions, duplicated coverage, data leakage, and label disagreement. Then compute what changes — and what does not — in the suite hash when you edit only `manifest.json`'s `owners` field, and explain why that is the intended behavior.
