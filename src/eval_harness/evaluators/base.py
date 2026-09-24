"""Evaluator protocol and shared finding helpers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from ..domain.cases import EvalCase
from ..domain.findings import FailureCode, Finding, Severity
from ..domain.outcomes import NormalizedOutcome

__all__ = [
    "Evaluator",
    "SchemaResolver",
    "make_finding",
    "normalize_text",
    "observed_outcome",
    "outcome_text",
]


@runtime_checkable
class Evaluator(Protocol):
    @property
    def evaluator_id(self) -> str: ...

    def evaluate(self, case: EvalCase, outcome: NormalizedOutcome) -> tuple[Finding, ...]: ...


class SchemaResolver(Protocol):
    """Resolve a suite JSON Schema identifier to a Draft 2020-12 mapping."""

    def __call__(self, schema_id: str) -> dict[str, JsonValue] | None: ...


def make_finding(
    evaluator_id: str,
    code: FailureCode | str,
    *,
    passed: bool,
    severity: Severity,
    message: str = "",
    score: float | None = None,
    evidence: dict[str, JsonValue] | None = None,
) -> Finding:
    return Finding(
        evaluator_id=evaluator_id,
        code=str(code),
        severity=severity,
        passed=passed,
        score=score,
        message=message,
        evidence=evidence or {},
    )


def outcome_text(outcome: NormalizedOutcome) -> str:
    """Best-effort textual surface for deterministic concept checks."""

    parts: list[str] = []
    if outcome.text:
        parts.append(outcome.text)
    if outcome.structured is not None:
        import json

        parts.append(json.dumps(outcome.structured, ensure_ascii=False, sort_keys=True))
    for citation in outcome.citations:
        if citation.text:
            parts.append(citation.text)
    return "\n".join(parts)


def normalize_text(value: str) -> str:
    """NFC-normalize, trim, collapse internal whitespace, and casefold."""

    import unicodedata

    normalized = unicodedata.normalize("NFC", value).casefold()
    return " ".join(normalized.split())


_REFUSAL_MARKERS = (
    "i can't",
    "i cannot",
    "i won't",
    "i will not",
    "unable to",
    "must decline",
    "cannot help",
    "not able to",
)


def observed_outcome(outcome: NormalizedOutcome) -> str:
    """Best-effort observed outcome: answered, refused, or insufficient_evidence.

    A structured ``{"outcome": ...}`` field wins when present; otherwise a
    small refusal-marker heuristic is used, and empty output is treated as
    insufficient evidence.
    """

    allowed = {"answered", "refused", "insufficient_evidence"}
    if isinstance(outcome.structured, dict):
        declared = outcome.structured.get("outcome")
        if isinstance(declared, str) and declared in allowed:
            return declared
    text = normalize_text(outcome.text or "")
    if not text:
        return "insufficient_evidence"
    if any(marker in text for marker in _REFUSAL_MARKERS):
        return "refused"
    return "answered"
