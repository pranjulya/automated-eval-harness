# Reproducible Evaluation

Evaluation is a measurement pipeline, not a prompt script. The measured subject, inputs, procedure, instrument, environment, and decision policy all need identities. A run manifest binds those identities so another engineer can explain what changed.

Reproduction has two levels. Outcome replay proves that evaluators and gates produce the same result from the same normalized outcome. Live replay asks an external provider for another output and may differ even with temperature zero. The harness records that limitation instead of promising determinism it does not control.

Exercise: list every material field needed to distinguish a model change from a prompt, schema, retrieval, evaluator, or environment change.
