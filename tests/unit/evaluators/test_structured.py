"""Structured-output evaluator tests (Draft 2020-12 + assertions)."""

from __future__ import annotations

from pathlib import Path

from eval_harness.datasets import load_suite
from eval_harness.domain.findings import FailureCode
from eval_harness.domain.outcomes import NormalizedOutcome, OutcomeStatus
from eval_harness.evaluators.invariants import HARD_INVARIANT_SCHEMA
from eval_harness.evaluators.structured import StructuredEvaluator

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "order": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "total": {"type": "number"},
                "status": {"type": "string", "enum": ["new", "paid", "shipped"]},
                "quantity": {"type": "integer"},
                "items": {"type": "array"},
            },
            "required": ["id", "total", "status", "quantity", "items"],
            "additionalProperties": False,
        }
    },
    "required": ["order"],
    "additionalProperties": False,
}


def resolver(schema_id: str) -> dict | None:
    return SCHEMA if schema_id == "schema:order-nested-v1" else None


EVALUATOR = StructuredEvaluator(resolver)


def valid_document() -> dict:
    return {
        "order": {
            "id": "A1",
            "total": 10.0,
            "status": "paid",
            "quantity": 2,
            "items": [{}, {}, {}],
        }
    }


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings if not finding.passed}


def test_valid_structured_output_passes(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, structured=valid_document())
    assert EVALUATOR.evaluate(case, outcome) == ()


def test_wrong_type_fails_schema(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-002")
    document = valid_document()
    document["order"]["total"] = "ten"
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, structured=document)
    assert HARD_INVARIANT_SCHEMA in _codes(EVALUATOR.evaluate(case, outcome))


def test_wrong_enum_fails_schema(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-003")
    document = valid_document()
    document["order"]["status"] = "cancelled"
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, structured=document)
    assert HARD_INVARIANT_SCHEMA in _codes(EVALUATOR.evaluate(case, outcome))


def test_extra_field_rejected(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-004")
    document = valid_document()
    document["order"]["surprise"] = True
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, structured=document)
    assert HARD_INVARIANT_SCHEMA in _codes(EVALUATOR.evaluate(case, outcome))


def test_missing_field_fails_schema(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-005")
    document = valid_document()
    del document["order"]["id"]
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, structured=document)
    assert HARD_INVARIANT_SCHEMA in _codes(EVALUATOR.evaluate(case, outcome))


def test_numeric_range_assertion(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-006")
    ok = valid_document()
    bad = valid_document()
    bad["order"]["quantity"] = 20
    assert EVALUATOR.evaluate(case, NormalizedOutcome(status=OutcomeStatus.OK, structured=ok)) == ()
    assert FailureCode.BUSINESS_ASSERTION_FAILED in _codes(
        EVALUATOR.evaluate(case, NormalizedOutcome(status=OutcomeStatus.OK, structured=bad))
    )


def test_array_cardinality_assertion(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-010")
    bad = valid_document()
    bad["order"]["items"] = [{}, {}]
    assert FailureCode.BUSINESS_ASSERTION_FAILED in _codes(
        EVALUATOR.evaluate(case, NormalizedOutcome(status=OutcomeStatus.OK, structured=bad))
    )


def test_missing_structured_output_fails(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="not json")
    assert HARD_INVARIANT_SCHEMA in _codes(EVALUATOR.evaluate(case, outcome))


def test_unresolved_schema_fails_closed(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("struct-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, structured=valid_document())
    evaluator = StructuredEvaluator(None)
    assert HARD_INVARIANT_SCHEMA in _codes(evaluator.evaluate(case, outcome))
