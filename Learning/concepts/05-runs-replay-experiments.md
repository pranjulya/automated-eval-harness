# Runs, Replay, and Experiments

An immutable run bundle is the experiment record: inputs, attempts, outcomes, findings, aggregates, comparison, and hashes. Atomic finalization keeps half-written evidence from appearing valid. Reports are projections; machine-readable records remain authoritative.

Replay applies current-compatible evaluators to recorded normalized outcomes. It helps find scoring bugs cheaply. A useful experiment changes one material variable, but multi-variable comparisons are allowed when marked non-attributable rather than given a false causal story.

Exercise: inspect a conceptual bundle and identify which files are raw evidence, decisions, projections, and integrity markers.
