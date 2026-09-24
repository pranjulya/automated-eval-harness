"""Unit tests for strict, discriminated case models."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from eval_harness.domain.cases import Profile, parse_case, validate_case_id


def text_case(**overrides: Any) -> dict[str, Any]:
    case: dict[str, Any] = {
        "schema_version": "eval.case.v1",
        "case_id": "text-001",
        "title": "Example",
        "primary_profile": "text_semantic",
        "tags": ["factual"],
        "weight": 1,
        "input": {"messages": [{"role": "user", "content": "hello"}]},
        "expectation": {
            "outcome": "answered",
            "deterministic": {
                "kind": "text",
                "required_values": ["hello"],
                "forbidden_values": [],
                "normalized_match": True,
                "trusted_regex": [],
            },
            "semantic": None,
        },
        "limits": {"timeout_ms": 1000, "max_output_bytes": 1024},
        "provenance": {
            "author": "a",
            "reviewers": ["r"],
            "source_classification": "synthetic",
            "rationale": "because",
        },
    }
    case.update(overrides)
    return case


def test_text_case_parses() -> None:
    case = parse_case(text_case())
    assert case.case_id == "text-001"
    assert case.primary_profile is Profile.TEXT_SEMANTIC
    assert case.weight == 1


def test_unknown_top_level_field_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_case(text_case(extra="nope"))


def test_unknown_deterministic_field_rejected() -> None:
    payload = text_case()
    payload["expectation"]["deterministic"]["surprise"] = 1
    with pytest.raises(ValidationError):
        parse_case(payload)


@pytest.mark.parametrize("case_id", ["text1", "text-01", "TEXT-001", "text-0001", "other-001"])
def test_invalid_case_ids_rejected(case_id: str) -> None:
    assert validate_case_id(case_id) is False
    with pytest.raises(ValidationError):
        parse_case(text_case(case_id=case_id))


def test_case_id_prefix_must_match_profile() -> None:
    with pytest.raises(ValidationError, match="prefix"):
        parse_case(text_case(case_id="rag-001"))


def test_unknown_tag_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown tags"):
        parse_case(text_case(tags=["not-a-tag"]))


def test_duplicate_tags_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate tags"):
        parse_case(text_case(tags=["factual", "factual"]))


def test_weight_must_be_one() -> None:
    with pytest.raises(ValidationError, match="weight"):
        parse_case(text_case(weight=2))


def test_rag_answerable_requires_evidence() -> None:
    payload = text_case(
        case_id="rag-001",
        primary_profile="rag",
        expectation={
            "outcome": "answered",
            "deterministic": {
                "kind": "rag",
                "answerable": True,
                "relevant_evidence": [],
                "recall_k": [5],
                "required_citation_ids": [],
            },
        },
    )
    with pytest.raises(ValidationError, match="relevant_evidence"):
        parse_case(payload)


def test_rag_unanswerable_forbids_evidence() -> None:
    payload = text_case(
        case_id="rag-002",
        primary_profile="rag",
        expectation={
            "outcome": "answered",
            "deterministic": {
                "kind": "rag",
                "answerable": False,
                "relevant_evidence": [{"document_id": "d", "evidence_id": "e", "grade": 2}],
                "recall_k": [],
                "required_citation_ids": [],
            },
        },
    )
    with pytest.raises(ValidationError, match="must not declare"):
        parse_case(payload)


def test_wrong_expectation_shape_for_profile_rejected() -> None:
    payload = text_case(
        primary_profile="structured_output",
        expectation={
            "outcome": "answered",
            "deterministic": {"kind": "text", "required_values": ["x"]},
        },
    )
    with pytest.raises(ValidationError):
        parse_case(payload)


def test_safety_case_parses() -> None:
    case = parse_case(
        text_case(
            case_id="safe-001",
            primary_profile="safety_abstention",
            expectation={
                "outcome": "refused",
                "deterministic": {
                    "kind": "safety",
                    "required_outcome": "refused",
                    "forbidden_patterns": ["secret"],
                    "canaries": ["CANARY"],
                },
            },
        )
    )
    assert case.primary_profile is Profile.SAFETY_ABSTENTION
