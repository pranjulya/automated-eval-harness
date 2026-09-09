# Extension Profiles

Profiles differ in observable evidence, not lifecycle. Structured output adds parsed values/schema assertions. RAG adds ranked evidence, claims, citations, and no-answer. Tool use adds a trace of names, arguments, order, and termination. All still validate, invoke, score, aggregate, compare, and persist through one runner.

Citation validity asks whether the ID is approved; correctness asks whether evidence supports the claim; completeness asks whether material claims are cited. Tool correctness likewise separates selection, arguments, order, and safety. Keeping dimensions separate makes failures repairable.

Exercise: add a conceptual classification profile by naming only its expectation, normalized evidence, deterministic evaluator, report projection, and tests—without inventing a plugin loader or second runner.
