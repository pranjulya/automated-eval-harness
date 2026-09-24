"""Normalized target outcomes.

An adapter maps untrusted provider data into exactly one of these immutable
shapes. Evaluators consume them and never touch transports.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue

__all__ = [
    "Citation",
    "EvidenceHit",
    "NormalizedOutcome",
    "OutcomeStatus",
    "ToolCall",
    "Usage",
]


class OutcomeStatus(StrEnum):
    OK = "ok"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    TRANSPORT_ERROR = "transport_error"
    TARGET_ERROR = "target_error"
    MALFORMED_RESPONSE = "malformed_response"


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class EvidenceHit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    evidence_id: str
    rank: int = Field(ge=1)
    score: float | None = None


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    evidence_ids: tuple[str, ...] = ()
    text: str | None = None


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    call_id: str | None = None
    succeeded: bool = True


class NormalizedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: OutcomeStatus
    text: str | None = None
    structured: JsonValue = None
    evidence: tuple[EvidenceHit, ...] = ()
    citations: tuple[Citation, ...] = ()
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = Field(default_factory=Usage)
    latency_ms: int | None = Field(default=None, ge=0)
    raw_artifact_ref: str | None = None

    @property
    def usable(self) -> bool:
        return self.status is OutcomeStatus.OK
