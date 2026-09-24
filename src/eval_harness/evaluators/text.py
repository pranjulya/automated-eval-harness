"""Text/semantic deterministic evaluator."""

from __future__ import annotations

import re

from ..domain.cases import EvalCase, TextCase
from ..domain.findings import FailureCode, Finding, Severity
from ..domain.outcomes import NormalizedOutcome
from .base import Evaluator, make_finding, normalize_text

__all__ = ["TextEvaluator"]

EVALUATOR_ID = "text.v1"


class TextEvaluator(Evaluator):
    @property
    def evaluator_id(self) -> str:
        return EVALUATOR_ID

    def evaluate(self, case: EvalCase, outcome: NormalizedOutcome) -> tuple[Finding, ...]:
        if not isinstance(case, TextCase):
            return ()
        deterministic = case.expectation.deterministic
        raw = outcome.text or ""
        normalized = normalize_text(raw)
        findings: list[Finding] = []

        for required in deterministic.required_values:
            if normalize_text(required) not in normalized:
                findings.append(
                    make_finding(
                        EVALUATOR_ID,
                        FailureCode.TEXT_ASSERTION_FAILED,
                        passed=False,
                        severity=Severity.DETERMINISTIC,
                        message="required value missing",
                        evidence={"required": required},
                    )
                )
        for forbidden in deterministic.forbidden_values:
            needle = normalize_text(forbidden)
            if needle and needle in normalized:
                findings.append(
                    make_finding(
                        EVALUATOR_ID,
                        FailureCode.TEXT_ASSERTION_FAILED,
                        passed=False,
                        severity=Severity.DETERMINISTIC,
                        message="forbidden value present",
                        evidence={"forbidden": forbidden},
                    )
                )
        for pattern in deterministic.trusted_regex:
            if re.search(pattern, raw, flags=re.IGNORECASE) is None:
                findings.append(
                    make_finding(
                        EVALUATOR_ID,
                        FailureCode.TEXT_ASSERTION_FAILED,
                        passed=False,
                        severity=Severity.DETERMINISTIC,
                        message="trusted regex did not match",
                        evidence={"pattern": pattern},
                    )
                )
        return tuple(findings)
