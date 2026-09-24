# Extension Profiles

A profile extends three typed points and reuses everything else: the dataset
loader, runner, artifact format, aggregation, gate engine, and reports. There is
no dynamic plugin loader.

## The three extension points

1. **Case expectation** — a discriminated Pydantic model selected by
   `primary_profile`. Add a `Literal` profile value and an expectation model with
   `extra="forbid"`.
2. **Normalized evidence** — what the adapter must produce for this profile,
   expressed through the existing `NormalizedOutcome` fields (`structured`,
   `evidence`, `citations`, `tool_calls`, `text`, `usage`).
3. **Evaluator** — an object with `evaluator_id` and
   `evaluate(case, outcome) -> tuple[Finding, ...]`, registered in
   `evaluators/__init__.py::build_registry`.

## Worked example

```python
# 1. Expectation (domain/cases.py)
class ClassificationCase(_CaseBase):
    primary_profile: Literal[Profile.CLASSIFICATION] = Profile.CLASSIFICATION
    expectation: ClassificationExpectation

# 2. Evaluator (evaluators/classification.py)
class ClassificationEvaluator:
    @property
    def evaluator_id(self) -> str:
        return "classification.v1"

    def evaluate(self, case, outcome):
        if not isinstance(case, ClassificationCase):
            return ()
        # read outcome.structured, emit Finding records with stable codes
        ...

# 3. Registry (evaluators/__init__.py)
Profile.CLASSIFICATION: (ClassificationEvaluator(),),
```

Then add case fixtures, a golden distribution entry, a report projection if the
profile has diagnostic metrics, and contract tests proving fake/HTTP parity. No
runner, persistence, aggregation, or gate change is needed — those are
profile-independent by construction.

## What a profile may not do

- Replace the run lifecycle, artifact format, replay, or comparison.
- Add a second scoring path that bypasses hard invariants.
- Execute untrusted code or load plugins dynamically.

## Diagnostics

Profile-specific metric findings use `Severity.INFO` with a numeric `score`
(e.g. `INFO_RECALL_AT_K`, `INFO_MRR`, `INFO_NDCG_AT_K`). The Markdown report
renders a **Profile diagnostics** section by averaging those scores per profile;
the gate engine ignores `INFO` findings, so diagnostics never change a decision.
