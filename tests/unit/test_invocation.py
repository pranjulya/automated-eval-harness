"""Invocation service retry-policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_harness.adapters.targets.base import AttemptResult, TargetConfig, TargetIdentity
from eval_harness.application.invocation import InvocationService, RetryPolicy
from eval_harness.datasets import load_suite
from eval_harness.domain.outcomes import NormalizedOutcome, OutcomeStatus

GOLDEN = load_suite(Path(__file__).resolve().parents[2] / "evaluation" / "datasets" / "golden-v1")


class ScriptedAdapter:
    def __init__(self, states: list[OutcomeStatus]) -> None:
        self._states = states
        self.calls = 0

    @property
    def adapter_id(self) -> str:
        return "scripted"

    def identity(self, config: TargetConfig) -> TargetIdentity:
        return TargetIdentity(
            adapter="scripted",
            adapter_version="1.0.0",
            endpoint_id="scripted://test",
            request_template_hash="sha256:x",
            model=config.model,
            deterministic=True,
            seed_supported=False,
            externally_nondeterministic=False,
        )

    def invoke(self, case, config: TargetConfig) -> AttemptResult:
        state = self._states[min(self.calls, len(self._states) - 1)]
        self.calls += 1
        return AttemptResult(
            state=state,
            outcome=NormalizedOutcome(status=state),
            attempt_index=1,
            request_hash=f"hash-{self.calls}",
            error=None if state is OutcomeStatus.OK else state.value,
        )


def _case():
    return GOLDEN.by_id("text-001")


def _config(*, idempotent: bool) -> TargetConfig:
    return TargetConfig(adapter="scripted", model="m", idempotent=idempotent)


def test_default_policy_is_single_attempt() -> None:
    adapter = ScriptedAdapter([OutcomeStatus.TIMEOUT, OutcomeStatus.OK])
    record = InvocationService(sleeper=lambda _s: None).invoke(
        _case(), adapter, _config(idempotent=True)
    )
    assert len(record.attempts) == 1
    assert adapter.calls == 1


def test_idempotent_retry_up_to_three() -> None:
    adapter = ScriptedAdapter(
        [OutcomeStatus.TIMEOUT, OutcomeStatus.TRANSPORT_ERROR, OutcomeStatus.OK]
    )
    record = InvocationService(sleeper=lambda _s: None).invoke(
        _case(), adapter, _config(idempotent=True), RetryPolicy(max_attempts=3)
    )
    assert len(record.attempts) == 3
    assert record.outcome.status is OutcomeStatus.OK


def test_non_idempotent_is_not_retried() -> None:
    adapter = ScriptedAdapter([OutcomeStatus.TIMEOUT, OutcomeStatus.OK])
    record = InvocationService(sleeper=lambda _s: None).invoke(
        _case(), adapter, _config(idempotent=False), RetryPolicy(max_attempts=3)
    )
    assert len(record.attempts) == 1


def test_malformed_response_is_not_retried() -> None:
    adapter = ScriptedAdapter([OutcomeStatus.MALFORMED_RESPONSE, OutcomeStatus.OK])
    record = InvocationService(sleeper=lambda _s: None).invoke(
        _case(), adapter, _config(idempotent=True), RetryPolicy(max_attempts=3)
    )
    assert len(record.attempts) == 1
    assert record.outcome.status is OutcomeStatus.MALFORMED_RESPONSE


def test_backoff_is_bounded_and_doubles() -> None:
    delays: list[float] = []
    adapter = ScriptedAdapter([OutcomeStatus.TIMEOUT])
    InvocationService(sleeper=delays.append).invoke(
        _case(),
        adapter,
        _config(idempotent=True),
        RetryPolicy(max_attempts=3, base_backoff_ms=100, max_backoff_ms=250),
    )
    assert delays == [0.1, 0.2]
    assert all(delay <= 0.25 for delay in delays)


def test_every_attempt_is_preserved() -> None:
    adapter = ScriptedAdapter([OutcomeStatus.TIMEOUT, OutcomeStatus.TIMEOUT, OutcomeStatus.OK])
    record = InvocationService(sleeper=lambda _s: None).invoke(
        _case(), adapter, _config(idempotent=True), RetryPolicy(max_attempts=3)
    )
    assert [attempt.attempt_index for attempt in record.attempts] == [1, 2, 3]
    assert [attempt.state for attempt in record.attempts] == [
        OutcomeStatus.TIMEOUT,
        OutcomeStatus.TIMEOUT,
        OutcomeStatus.OK,
    ]


def test_interruption_propagates() -> None:
    def sleeper(_seconds: float) -> None:
        raise KeyboardInterrupt

    adapter = ScriptedAdapter([OutcomeStatus.TIMEOUT])
    with pytest.raises(KeyboardInterrupt):
        InvocationService(sleeper=sleeper).invoke(
            _case(), adapter, _config(idempotent=True), RetryPolicy(max_attempts=3)
        )
