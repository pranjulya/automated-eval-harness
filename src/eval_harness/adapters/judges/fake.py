"""Deterministic fake judge backed by static, case-keyed fixtures."""

from __future__ import annotations

from collections.abc import Mapping

from ...domain.judging import JudgeRequest
from ...errors import JudgeInvalidError, JudgeUnavailableError
from .base import JudgeConfig, RawJudgeResponse

__all__ = ["FakeJudgeAdapter"]


class FakeJudgeAdapter:
    """Map ``f"{rubric_id}|{case_id}"`` (or ``case_id``) to a raw judge response.

    A missing key raises ``JudgeUnavailableError``; an unusable entry raises
    ``JudgeInvalidError``. Both are fail-closed conditions.
    """

    def __init__(self, responses: Mapping[str, Mapping[str, object]]) -> None:
        self._responses = {key: dict(value) for key, value in responses.items()}

    @property
    def adapter_id(self) -> str:
        return "fake-judge"

    def judge(self, request: JudgeRequest, config: JudgeConfig) -> RawJudgeResponse:
        del config
        entry = self._responses.get(f"{request.rubric_id}|{request.case_id}")
        if entry is None:
            entry = self._responses.get(request.case_id)
        if entry is None:
            raise JudgeUnavailableError(
                "no fake judge response",
                details={"case_id": request.case_id, "rubric_id": request.rubric_id},
            )
        if "error" in entry:
            raise JudgeUnavailableError(str(entry["error"]), details={"case_id": request.case_id})
        try:
            return RawJudgeResponse.model_validate(entry)
        except Exception as error:
            raise JudgeInvalidError(
                "fake judge response violates the contract",
                details={"case_id": request.case_id},
            ) from error
