"""RAG deterministic evaluator tests."""

from __future__ import annotations

from pathlib import Path

from eval_harness.datasets import load_suite
from eval_harness.domain.findings import FailureCode
from eval_harness.domain.outcomes import (
    Citation,
    EvidenceHit,
    NormalizedOutcome,
    OutcomeStatus,
)
from eval_harness.evaluators.rag import RagEvaluator

EVALUATOR = RagEvaluator()


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings if not finding.passed}


def _hit(evidence_id: str, rank: int, document_id: str = "policy-v1") -> EvidenceHit:
    return EvidenceHit(document_id=document_id, evidence_id=evidence_id, rank=rank)


def test_answerable_with_correct_citation_passes(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-001")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        evidence=(_hit("policy-p1", 1),),
        citations=(Citation(claim_id="c1", evidence_ids=("policy-p1",)),),
        text="The cancellation period is 30 days.",
    )
    assert _codes(EVALUATOR.evaluate(case, outcome)) == set()


def test_recall_miss_is_reported(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-006")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, evidence=(_hit("policy-p1", 1),))
    assert FailureCode.RETRIEVAL_MISS in _codes(EVALUATOR.evaluate(case, outcome))


def test_context_evidence_lost_is_reported(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-007")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, evidence=(_hit("other", 1),))
    assert FailureCode.CONTEXT_EVIDENCE_LOST in _codes(EVALUATOR.evaluate(case, outcome))


def test_citation_completeness_is_reported(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-004")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        evidence=(_hit("policy-p1", 1), _hit("handbook-p1", 2, "handbook-v1")),
        citations=(Citation(claim_id="c1", evidence_ids=("policy-p1",)),),
    )
    assert FailureCode.CITATION_INCOMPLETE in _codes(EVALUATOR.evaluate(case, outcome))


def test_no_answer_false_positive(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-010")
    answered = NormalizedOutcome(status=OutcomeStatus.OK, text="The address is 1 Main St.")
    abstained = NormalizedOutcome(status=OutcomeStatus.OK, text="")
    assert FailureCode.NO_ANSWER_FALSE_POSITIVE in _codes(EVALUATOR.evaluate(case, answered))
    assert _codes(EVALUATOR.evaluate(case, abstained)) == set()


def test_graded_ndcg_diagnostic(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-005")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        evidence=(_hit("policy-p1", 1), _hit("policy-p2", 2)),
        citations=(Citation(claim_id="c1", evidence_ids=("policy-p1",)),),
    )
    findings = EVALUATOR.evaluate(case, outcome)
    ndcg = [finding for finding in findings if finding.code == "INFO_NDCG_AT_K"]
    assert ndcg
    assert ndcg[0].score == 1.0


def test_relevant_but_uncited_case_reports_missing_citation(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("rag-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, evidence=(_hit("policy-p1", 1),))
    assert FailureCode.CITATION_INCOMPLETE in _codes(EVALUATOR.evaluate(case, outcome))
