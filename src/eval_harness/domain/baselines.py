"""Immutable baseline records and explicit promotion authorization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..datasets.hashing import canonical_json, sha256_hex

__all__ = [
    "BASELINE_SCHEMA_VERSION",
    "BaselineRecord",
    "PromotionAuthorization",
    "baseline_record_hash",
]

BASELINE_SCHEMA_VERSION = "eval.baseline.v1"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PromotionAuthorization(_Model):
    actor: str = Field(min_length=1)
    approval_evidence: tuple[str, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)


class BaselineRecord(_Model):
    schema_version: str = BASELINE_SCHEMA_VERSION
    suite_name: str
    channel: str
    run_id: str
    suite_hash: str
    schema_version_of_suite: str
    evaluator_version: str
    gate_policy_hash: str
    run_manifest_hash: str
    approver: str
    approval_evidence: tuple[str, ...]
    reason: str
    created: str
    superseded: str | None = None
    record_hash: str = ""


def baseline_record_hash(record: BaselineRecord) -> str:
    payload = record.model_dump(mode="json")
    payload.pop("record_hash", None)
    return sha256_hex(canonical_json(payload))
