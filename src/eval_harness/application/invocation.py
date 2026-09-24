"""Application service that invokes a target and preserves every attempt."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from ..adapters.targets.base import AttemptResult, TargetAdapter, TargetConfig, TargetIdentity
from ..domain.cases import EvalCase
from ..domain.outcomes import NormalizedOutcome, OutcomeStatus

__all__ = ["RETRYABLE_STATES", "InvocationRecord", "InvocationService", "RetryPolicy"]

RETRYABLE_STATES: frozenset[OutcomeStatus] = frozenset(
    {OutcomeStatus.TIMEOUT, OutcomeStatus.RATE_LIMITED, OutcomeStatus.TRANSPORT_ERROR}
)


class RetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_attempts: int = Field(default=1, ge=1, le=3)
    base_backoff_ms: int = Field(default=100, ge=0)
    max_backoff_ms: int = Field(default=1_000, ge=0)


@dataclass(frozen=True, slots=True)
class InvocationRecord:
    case_id: str
    target_identity: TargetIdentity
    attempts: tuple[AttemptResult, ...]

    @property
    def outcome(self) -> NormalizedOutcome:
        return self.attempts[-1].outcome

    @property
    def request_hash(self) -> str:
        return self.attempts[0].request_hash

    @property
    def errored(self) -> bool:
        return self.outcome.status is not OutcomeStatus.OK


class InvocationService:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock = clock
        self._sleeper = sleeper

    def invoke(
        self,
        case: EvalCase,
        adapter: TargetAdapter,
        config: TargetConfig,
        policy: RetryPolicy | None = None,
    ) -> InvocationRecord:
        active = policy if policy is not None else RetryPolicy()
        attempts: list[AttemptResult] = []
        for index in range(1, active.max_attempts + 1):
            started = self._clock()
            result = adapter.invoke(case, config)
            elapsed_ms = int((self._clock() - started) * 1000)
            attempts.append(
                AttemptResult(
                    state=result.state,
                    outcome=result.outcome,
                    attempt_index=index,
                    request_hash=result.request_hash,
                    http_status=result.http_status,
                    response_hash=result.response_hash,
                    error=result.error,
                    elapsed_ms=result.elapsed_ms if result.elapsed_ms is not None else elapsed_ms,
                    retry_reason=result.retry_reason,
                )
            )
            if result.state is OutcomeStatus.OK:
                break
            if result.state not in RETRYABLE_STATES:
                break
            if not config.idempotent:
                break
            if index == active.max_attempts:
                break
            self._sleeper(self._backoff(active, index))
        return InvocationRecord(
            case_id=case.case_id,
            target_identity=adapter.identity(config),
            attempts=tuple(attempts),
        )

    @staticmethod
    def _backoff(policy: RetryPolicy, index: int) -> float:
        delay_ms: int = min(policy.max_backoff_ms, policy.base_backoff_ms * (2 ** (index - 1)))
        return float(delay_ms) / 1000.0
