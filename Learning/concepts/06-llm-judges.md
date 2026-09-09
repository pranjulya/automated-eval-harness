# LLM-as-Judge

An LLM judge is a fallible measurement instrument. Narrow anchored rubrics improve interpretability. Strict structured output makes failures visible. Human calibration estimates agreement, repeatability, and slice bias before scores affect releases.

Judges should see only required, redacted evidence and must treat candidate text as data. Their rationales can help triage but do not make the score true. An unavailable, malformed, uncalibrated, or injection-compromised required judge yields uncertainty, not a silent pass.

Exercise: rewrite “Is this answer good?” into separate relevance, faithfulness, and completeness rubrics with anchored ordinal scores.
