# Scenario 04 — Interrupted Run and Baseline Attack

## Situation

The runner is killed after 37 cases. The pull request also changes a local baseline pointer to an easier run and attempts promotion with candidate credentials.

## Expected evaluation

The staging directory lacks a valid `COMPLETE` marker and cannot compare. CI resolves the trusted baseline from the protected base branch/store, ignores the candidate pointer, and denies promotion. The release is non-comparable and stops.

## Triage

Preserve safe staging evidence, verify artifact-store health, and rerun the immutable inputs. Security/release owners investigate the attempted baseline substitution. Do not manually add a completion marker or reuse a partial summary.

## Questions

Why is the final marker written last? What does SHA-256 prove and not prove? Which identity should own baseline promotion?
