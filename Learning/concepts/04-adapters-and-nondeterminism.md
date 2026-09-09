# Adapters and Nondeterminism

An adapter translates transport/provider details into one normalized outcome. It records model/config evidence but does not decide quality. Separating transport states from semantic results prevents timeouts, malformed data, and wrong answers from becoming one vague failure.

Retries are safe only when the operation and failure point make repetition safe. Record every attempt. A stable seed and temperature zero can reduce variation but do not guarantee identical external inference; provider aliases, infrastructure, and hidden model changes still matter.

Exercise: decide retry behavior for connection refusal, 429, read timeout after request acceptance, schema-invalid output, and forbidden tool selection.
