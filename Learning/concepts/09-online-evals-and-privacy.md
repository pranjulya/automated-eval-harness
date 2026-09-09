# Online Evaluation and Privacy

Offline evaluation answers “may we release this candidate?” Online evaluation asks “is production behavior drifting or revealing new failure modes?” Traffic is not automatically labeled truth. Sampling can be biased and production data can contain personal, confidential, or regulated information.

Consent and eligibility precede collection; redaction precedes persistence; quarantine restricts uncertain data; retention and deletion are enforceable. Human review turns a sanitized observation into a proposed golden case through normal versioning.

Exercise: trace a production response containing an email, account ID, and secret-like token through sample rejection, redaction/quarantine, access, retention, and deletion.
