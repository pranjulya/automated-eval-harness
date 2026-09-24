"""Deterministic fake target backed by static, case-keyed fixtures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from ...datasets.hashing import canonical_json, sha256_hex
from ...domain.cases import EvalCase
from ...domain.outcomes import NormalizedOutcome, OutcomeStatus
from .base import AttemptResult, TargetConfig, TargetIdentity

__all__ = ["FakeTargetAdapter", "load_fake_responses"]


def load_fake_responses(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fake response fixture must be a JSON object keyed by case_id")
    return {str(key): value for key, value in payload.items()}


class FakeTargetAdapter:
    """Return pre-recorded, case-keyed responses with no network access."""

    def __init__(self, responses: Mapping[str, Mapping[str, object]]) -> None:
        self._responses = {key: dict(value) for key, value in responses.items()}

    @property
    def adapter_id(self) -> str:
        return "fake"

    def identity(self, config: TargetConfig) -> TargetIdentity:
        return TargetIdentity(
            adapter="fake",
            adapter_version=config.adapter_version,
            endpoint_id="fake://in-memory",
            request_template_hash=config.request_template_hash,
            model=config.model,
            deterministic=True,
            seed_supported=True,
            externally_nondeterministic=False,
        )

    def invoke(self, case: EvalCase, config: TargetConfig) -> AttemptResult:
        request_hash = sha256_hex(
            canonical_json({"case_id": case.case_id, "input": case.input.model_dump(mode="json")})
        )
        entry = self._responses.get(case.case_id)
        if entry is None:
            outcome = NormalizedOutcome(
                status=OutcomeStatus.TARGET_ERROR,
                raw_artifact_ref=None,
            )
            return AttemptResult(
                state=OutcomeStatus.TARGET_ERROR,
                outcome=outcome,
                attempt_index=1,
                request_hash=request_hash,
                error="missing fake response fixture",
            )
        try:
            outcome = NormalizedOutcome.model_validate(entry)
        except ValidationError:
            outcome = NormalizedOutcome(status=OutcomeStatus.MALFORMED_RESPONSE)
            return AttemptResult(
                state=OutcomeStatus.MALFORMED_RESPONSE,
                outcome=outcome,
                attempt_index=1,
                request_hash=request_hash,
                error="invalid fake response fixture",
            )
        return AttemptResult(
            state=outcome.status,
            outcome=outcome,
            attempt_index=1,
            request_hash=request_hash,
            response_hash=sha256_hex(canonical_json(entry)),
        )
