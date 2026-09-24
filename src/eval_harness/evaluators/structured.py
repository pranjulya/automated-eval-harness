"""Structured-output evaluator (JSON Schema Draft 2020-12).

`jsonschema` is confined to this module. Domain code stays free of it.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from ..domain.cases import Assertion, EvalCase, StructuredCase
from ..domain.findings import FailureCode, Finding, Severity
from ..domain.outcomes import NormalizedOutcome
from .base import Evaluator, SchemaResolver, make_finding
from .invariants import HARD_INVARIANT_SCHEMA

__all__ = ["StructuredEvaluator"]

EVALUATOR_ID = "structured.v1"


def _null_resolver(schema_id: str) -> None:
    del schema_id
    return None


class StructuredEvaluator(Evaluator):
    def __init__(self, resolver: SchemaResolver | None = None) -> None:
        self._resolver: SchemaResolver = resolver or _null_resolver

    @property
    def evaluator_id(self) -> str:
        return EVALUATOR_ID

    def evaluate(self, case: EvalCase, outcome: NormalizedOutcome) -> tuple[Finding, ...]:
        if not isinstance(case, StructuredCase):
            return ()
        deterministic = case.expectation.deterministic
        if outcome.structured is None:
            return (
                make_finding(
                    EVALUATOR_ID,
                    HARD_INVARIANT_SCHEMA,
                    passed=False,
                    severity=Severity.HARD_INVARIANT,
                    message="no structured output was produced",
                ),
            )
        findings = list(_schema_findings(self._resolver, deterministic.json_schema_id, outcome))
        findings.extend(_assertion_findings(deterministic.assertions, outcome))
        return tuple(findings)


def _schema_findings(
    resolver: SchemaResolver, schema_id: str, outcome: NormalizedOutcome
) -> list[Finding]:
    schema = resolver(schema_id)
    if schema is None:
        return [
            make_finding(
                EVALUATOR_ID,
                HARD_INVARIANT_SCHEMA,
                passed=False,
                severity=Severity.HARD_INVARIANT,
                message="referenced JSON schema could not be resolved",
                evidence={"json_schema_id": schema_id},
            )
        ]
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(outcome.structured)
    except (ValidationError, SchemaError) as error:
        return [
            make_finding(
                EVALUATOR_ID,
                HARD_INVARIANT_SCHEMA,
                passed=False,
                severity=Severity.HARD_INVARIANT,
                message="structured output violates its required schema",
                evidence={"json_schema_id": schema_id, "detail": str(error.message)[:200]},
            )
        ]
    return []


def _assertion_findings(
    assertions: tuple[Assertion, ...], outcome: NormalizedOutcome
) -> list[Finding]:
    findings: list[Finding] = []
    for assertion in assertions:
        if not _assert(assertion, outcome.structured):
            findings.append(
                make_finding(
                    EVALUATOR_ID,
                    FailureCode.BUSINESS_ASSERTION_FAILED,
                    passed=False,
                    severity=Severity.DETERMINISTIC,
                    message="JSON Pointer assertion failed",
                    evidence={"pointer": assertion.pointer, "op": assertion.op},
                )
            )
    return findings


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def pointer_get(document: Any, pointer: str) -> tuple[bool, Any]:
    if pointer in ("", "/"):
        return True, document
    if not pointer.startswith("/"):
        return False, None
    current = document
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return False, None
    return True, current


def _assert(assertion: Assertion, document: Any) -> bool:
    found, value = pointer_get(document, assertion.pointer)
    result = False
    if assertion.op == "exists":
        result = found
    elif not found:
        result = False
    elif assertion.op == "equals":
        result = value == assertion.value
    elif assertion.op == "type":
        actual = _json_type(value)
        expected = assertion.value
        result = actual == expected or (expected == "number" and actual == "integer")
    elif assertion.op == "enum":
        result = isinstance(assertion.value, list) and value in assertion.value
    elif assertion.op == "range":
        result = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and (assertion.minimum is None or value >= assertion.minimum)
            and (assertion.maximum is None or value <= assertion.maximum)
        )
    elif assertion.op == "length":
        expected_length = assertion.value
        result = (
            isinstance(expected_length, int)
            and isinstance(value, (list, str, dict))
            and len(value) == expected_length
        )
    return not result if not assertion.expects else result
