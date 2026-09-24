"""RAG deterministic evaluator: retrieval, evidence, citation, no-answer."""

from __future__ import annotations

from ..domain.cases import EvalCase, RagCase
from ..domain.findings import FailureCode, Finding, Severity
from ..domain.metrics import (
    context_evidence_recall,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from ..domain.outcomes import NormalizedOutcome
from .base import Evaluator, make_finding, observed_outcome

__all__ = ["RagEvaluator"]

EVALUATOR_ID = "rag.v1"


class RagEvaluator(Evaluator):
    @property
    def evaluator_id(self) -> str:
        return EVALUATOR_ID

    def evaluate(self, case: EvalCase, outcome: NormalizedOutcome) -> tuple[Finding, ...]:
        if not isinstance(case, RagCase):
            return ()
        deterministic = case.expectation.deterministic
        retrieved = [hit.evidence_id for hit in sorted(outcome.evidence, key=lambda hit: hit.rank)]
        if not deterministic.answerable:
            return _no_answer_findings(outcome)
        relevant = {label.evidence_id for label in deterministic.relevant_evidence}
        grades = {label.evidence_id: label.grade for label in deterministic.relevant_evidence}
        return _answerable_findings(
            retrieved,
            relevant,
            grades,
            deterministic.recall_k,
            deterministic.required_citation_ids,
            outcome,
        )


def _no_answer_findings(outcome: NormalizedOutcome) -> tuple[Finding, ...]:
    if observed_outcome(outcome) == "answered":
        return (
            make_finding(
                EVALUATOR_ID,
                FailureCode.NO_ANSWER_FALSE_POSITIVE,
                passed=False,
                severity=Severity.DETERMINISTIC,
                message="answer produced for an unanswerable case",
            ),
        )
    return ()


def _answerable_findings(
    retrieved: list[str],
    relevant: set[str],
    grades: dict[str, int],
    recall_k: tuple[int, ...],
    required_citations: tuple[str, ...],
    outcome: NormalizedOutcome,
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    max_k = max(recall_k, default=5)

    if recall_at_k(retrieved, relevant, max_k) == 0:
        findings.append(
            make_finding(
                EVALUATOR_ID,
                FailureCode.RETRIEVAL_MISS,
                passed=False,
                severity=Severity.DETERMINISTIC,
                message="no relevant evidence retrieved",
                evidence={"k": max_k},
            )
        )
    if mrr(retrieved, relevant) == 0:
        findings.append(
            make_finding(
                EVALUATOR_ID,
                FailureCode.RETRIEVAL_MISS,
                passed=False,
                severity=Severity.DETERMINISTIC,
                message="no relevant evidence ranked",
            )
        )

    required = set(required_citations)
    retained = context_evidence_recall(retrieved, required)
    if retained is not None and retained < 1.0:
        findings.append(
            make_finding(
                EVALUATOR_ID,
                FailureCode.CONTEXT_EVIDENCE_LOST,
                passed=False,
                severity=Severity.DETERMINISTIC,
                message="required evidence lost from context",
                evidence={"missing": ",".join(sorted(required - set(retrieved)))},
            )
        )

    cited: set[str] = set()
    for citation in outcome.citations:
        cited.update(citation.evidence_ids)
    missing_citations = sorted(required - cited)
    if missing_citations:
        findings.append(
            make_finding(
                EVALUATOR_ID,
                FailureCode.CITATION_INCOMPLETE,
                passed=False,
                severity=Severity.DETERMINISTIC,
                message="required citations missing",
                evidence={"missing": ",".join(missing_citations)},
            )
        )

    findings.extend(_diagnostics(retrieved, relevant, grades, recall_k))
    return tuple(findings)


def _diagnostics(
    retrieved: list[str],
    relevant: set[str],
    grades: dict[str, int],
    recall_k: tuple[int, ...],
) -> list[Finding]:
    diagnostics: list[Finding] = []
    for k in recall_k:
        diagnostics.append(
            make_finding(
                EVALUATOR_ID,
                "INFO_RECALL_AT_K",
                passed=True,
                severity=Severity.INFO,
                score=recall_at_k(retrieved, relevant, k),
                evidence={"k": k},
            )
        )
    diagnostics.append(
        make_finding(
            EVALUATOR_ID,
            "INFO_PRECISION_AT_K",
            passed=True,
            severity=Severity.INFO,
            score=precision_at_k(retrieved, relevant, max(recall_k, default=5)),
        )
    )
    diagnostics.append(
        make_finding(
            EVALUATOR_ID,
            "INFO_MRR",
            passed=True,
            severity=Severity.INFO,
            score=mrr(retrieved, relevant),
        )
    )
    graded = ndcg_at_k(retrieved, grades, max(recall_k, default=5))
    if graded is not None:
        diagnostics.append(
            make_finding(
                EVALUATOR_ID,
                "INFO_NDCG_AT_K",
                passed=True,
                severity=Severity.INFO,
                score=graded,
            )
        )
    return diagnostics
