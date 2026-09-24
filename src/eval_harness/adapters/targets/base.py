"""Target adapter port, identity, and attempt records.

Adapters translate transport into the frozen :class:`NormalizedOutcome`
contract. They never decide pass/fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from ...domain.cases import EvalCase
from ...domain.outcomes import NormalizedOutcome, OutcomeStatus

__all__ = [
    "AttemptResult",
    "TargetAdapter",
    "TargetConfig",
    "TargetIdentity",
]


class TargetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter: str
    model: str
    base_url: str | None = None
    path: str = "/invoke"
    timeout_ms: int = Field(default=30_000, gt=0)
    max_response_bytes: int = Field(default=131_072, gt=0)
    auth_header_env: str | None = None
    request_template_hash: str = "sha256:embedded"
    idempotent: bool = False
    seed_supported: bool = False
    externally_nondeterministic: bool = False
    adapter_version: str = "1.0.0"


class TargetIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter: str
    adapter_version: str
    endpoint_id: str
    request_template_hash: str
    model: str
    deterministic: bool
    seed_supported: bool
    externally_nondeterministic: bool


@dataclass(frozen=True, slots=True)
class AttemptResult:
    state: OutcomeStatus
    outcome: NormalizedOutcome
    attempt_index: int
    request_hash: str
    http_status: int | None = None
    response_hash: str | None = None
    error: str | None = None
    elapsed_ms: int | None = None
    retry_reason: str | None = None


@runtime_checkable
class TargetAdapter(Protocol):
    @property
    def adapter_id(self) -> str: ...

    def identity(self, config: TargetConfig) -> TargetIdentity: ...

    def invoke(self, case: EvalCase, config: TargetConfig) -> AttemptResult: ...
