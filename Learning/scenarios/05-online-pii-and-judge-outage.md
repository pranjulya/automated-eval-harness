# Scenario 05 — Online PII and Judge Outage

## Situation

An opted-in online sample contains an email, account identifier, and secret-like token. Redaction cannot confidently remove all sensitive material. During the offline release run, the judge provider also returns malformed JSON.

## Expected evaluation

The online record is quarantined or rejected before normal persistence, access is restricted, and no golden is created. Offline deterministic results remain stored. Required semantic dimensions are unavailable, so the release returns `REVIEW_REQUIRED` or non-comparable according to run completeness policy; it never silently passes.

## Triage

Privacy/security owns quarantine and deletion/incident handling. Judge adapter/quality owner inspects the strict response failure and may perform a bounded retry. Human review can resolve semantics; production data must stay outside judge prompts unless policy explicitly permits it.

## Questions

Why is redaction not the same as consent? Why preserve deterministic scores during judge failure? Can this state be waived, and under what exact limits?
