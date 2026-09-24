"""Judge adapter port and configuration."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from ...domain.judging import JudgeRequest

__all__ = ["JudgeAdapter", "JudgeConfig", "RawJudgeResponse"]


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model: str
    timeout_ms: int = Field(default=30_000, gt=0)
    max_response_bytes: int = Field(default=65_536, gt=0)
    auth_header_env: str | None = None
    adapter_version: str = "1.0.0"


class RawJudgeResponse(BaseModel):
    """Untrusted judge output before the service maps it through a rubric."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ordinal: int = Field(ge=1, le=5)
    evidence_ids: tuple[str, ...] = ()
    rationale: str = ""


@runtime_checkable
class JudgeAdapter(Protocol):
    @property
    def adapter_id(self) -> str: ...

    def judge(self, request: JudgeRequest, config: JudgeConfig) -> RawJudgeResponse: ...
