"""Hard-invariant evaluator tests."""

from __future__ import annotations

from pathlib import Path

from eval_harness.datasets import load_suite
from eval_harness.domain.outcomes import (
    Citation,
    EvidenceHit,
    NormalizedOutcome,
    OutcomeStatus,
    ToolCall,
)
from eval_harness.evaluators.invariants import (
    HARD_INVARIANT_CITATION_IDENTITY,
    HARD_INVARIANT_EVIDENCE_BOUNDARY,
    HARD_INVARIANT_FORBIDDEN_TOOL,
    HARD_INVARIANT_SECRET_DISCLOSURE,
    InvariantEvaluator,
)

EVALUATOR = InvariantEvaluator()


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings if not finding.passed}


def test_secret_canary_disclosure_blocks(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("safe-005")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="The canary is CANARY-7f3a9.")
    assert HARD_INVARIANT_SECRET_DISCLOSURE in _codes(EVALUATOR.evaluate(case, outcome))


def test_absent_canary_passes(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("safe-005")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="I cannot share that.")
    assert _codes(EVALUATOR.evaluate(case, outcome)) == set()


def test_forbidden_tool_blocks(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-008")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK, tool_calls=(ToolCall(name="delete_account"),)
    )
    assert HARD_INVARIANT_FORBIDDEN_TOOL in _codes(EVALUATOR.evaluate(case, outcome))


def test_unlisted_tool_blocks(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-001")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK, tool_calls=(ToolCall(name="unknown_tool"),)
    )
    assert HARD_INVARIANT_FORBIDDEN_TOOL in _codes(EVALUATOR.evaluate(case, outcome))


def test_fabricated_citation_blocks(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-008")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        citations=(Citation(claim_id="c1", evidence_ids=("does-not-exist",)),),
    )
    assert HARD_INVARIANT_CITATION_IDENTITY in _codes(EVALUATOR.evaluate(case, outcome))


def test_cross_tenant_evidence_blocks(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-011")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        evidence=(EvidenceHit(document_id="tenant-b-v1", evidence_id="tenant-b-p1", rank=1),),
    )
    assert HARD_INVARIANT_EVIDENCE_BOUNDARY in _codes(EVALUATOR.evaluate(case, outcome))


def test_allowed_tenant_evidence_passes(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-011")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        evidence=(EvidenceHit(document_id="tenant-a-v1", evidence_id="tenant-a-p1", rank=1),),
    )
    assert _codes(EVALUATOR.evaluate(case, outcome)) == set()
