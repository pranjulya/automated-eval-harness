"""Immutable run, result, summary, and bundle schemas (``eval.run.v1``)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .cases import Profile
from .findings import CaseState, Finding
from .outcomes import Usage

__all__ = [
    "RUN_SCHEMA_VERSION",
    "AttemptRecord",
    "BundleIndex",
    "CaseResult",
    "CodeIdentity",
    "DatasetRef",
    "ProfileAggregate",
    "RunManifest",
    "RunOutcome",
    "RunStatus",
    "Summary",
]

RUN_SCHEMA_VERSION = "eval.run.v1"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class DatasetRef(_Model):
    name: str
    suite_version: str
    schema_version: str
    content_hash: str
    case_ids: tuple[str, ...]


class CodeIdentity(_Model):
    commit: str
    dirty: bool
    package_version: str


class AttemptRecord(_Model):
    run_id: str
    case_id: str
    attempt_index: int
    state: str
    request_hash: str
    response_hash: str | None = None
    http_status: int | None = None
    error: str | None = None
    elapsed_ms: int | None = None


class CaseResult(_Model):
    run_id: str
    case_id: str
    primary_profile: Profile
    sequence: int
    state: CaseState
    findings: tuple[Finding, ...] = ()
    outcome_hash: str | None = None
    attempts: int = 0
    latency_ms: int | None = None
    usage: Usage = Field(default_factory=Usage)
    redaction: tuple[str, ...] = ()


class ProfileAggregate(_Model):
    profile: Profile
    expected: int
    completed: int
    passed: int
    pass_rate: float | None = None


class Summary(_Model):
    schema_version: str = RUN_SCHEMA_VERSION
    run_id: str
    expected: int
    completed: int
    state_counts: dict[str, int]
    pass_rate: float | None = None
    profiles: tuple[ProfileAggregate, ...] = ()
    invariant_failures: int = 0
    semantic_reviews: int = 0
    p95_latency_ms: float | None = None
    total_cost_usd: float | None = None
    comparable: bool = False


class BundleIndex(_Model):
    schema_version: str = RUN_SCHEMA_VERSION
    run_id: str
    files: dict[str, str]
    index_hash: str
    created: str


class RunManifest(_Model):
    schema_version: str = RUN_SCHEMA_VERSION
    run_id: str
    status: RunStatus
    started_at: str
    finished_at: str | None = None
    command: str
    dataset: DatasetRef
    target: dict[str, object]
    evaluator_version: str
    retry_policy: dict[str, int]
    concurrency: int
    code: CodeIdentity
    environment: str
    requested_case_ids: tuple[str, ...]
    finished_case_ids: tuple[str, ...] = ()
    nondeterministic: bool = False


class RunOutcome(_Model):
    run_id: str
    status: RunStatus
    exit_code: int
    summary: Summary
    report_path: str
    bundle_path: str
    replay_of: str | None = None
