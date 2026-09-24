"""Online sample candidates: consent, redaction, quarantine, retention.

Online signals are quarantined observations. They may raise alerts and propose a
redacted draft case, but they can never publish datasets, rubrics, thresholds,
or baselines.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, JsonValue

__all__ = [
    "DEFAULT_TTLS",
    "SAMPLE_SCHEMA_VERSION",
    "DeletionEvidence",
    "OnlineSampleCandidate",
    "RedactionCatalog",
    "RetentionClass",
    "SampleState",
    "can_promote_to_case",
    "is_expired",
    "redact_value",
]

SAMPLE_SCHEMA_VERSION = "eval.online_sample.v1"


class RetentionClass(StrEnum):
    RUN_STANDARD = "run-standard"
    ONLINE_SHORT = "online-short"
    QUARANTINE_RESTRICTED = "quarantine-restricted"


class SampleState(StrEnum):
    QUARANTINED = "quarantined"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    DELETED = "deleted"


DEFAULT_TTLS: dict[RetentionClass, int] = {
    RetentionClass.RUN_STANDARD: 90,
    RetentionClass.ONLINE_SHORT: 7,
    RetentionClass.QUARANTINE_RESTRICTED: 30,
}

_DEFAULT_PATTERNS: tuple[str, ...] = (
    r"(?i)authorization:\s*\S+",
    r"Bearer\s+[A-Za-z0-9._-]+",
    r"sk-[A-Za-z0-9]{16,}",
    r"CANARY-[A-Za-z0-9-]+",
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RedactionCatalog(_Model):
    patterns: tuple[str, ...] = _DEFAULT_PATTERNS

    def redact(self, text: str) -> tuple[str, int]:
        hits = 0
        redacted = text
        for pattern in self.patterns:
            redacted, count = re.subn(pattern, "[REDACTED]", redacted)
            hits += count
        return redacted, hits


def redact_value(value: JsonValue, catalog: RedactionCatalog) -> tuple[JsonValue, int]:
    if isinstance(value, str):
        return catalog.redact(value)
    if isinstance(value, dict):
        total = 0
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            redacted, hits = redact_value(item, catalog)
            result[key] = redacted
            total += hits
        return result, total
    if isinstance(value, list):
        total = 0
        items: list[JsonValue] = []
        for item in value:
            redacted, hits = redact_value(item, catalog)
            items.append(redacted)
            total += hits
        return items, total
    return value, 0


class OnlineSampleCandidate(_Model):
    schema_version: str = SAMPLE_SCHEMA_VERSION
    sample_id: str
    tenant: str
    consent: bool
    classification: str
    state: SampleState
    payload: JsonValue
    redaction_hits: int = 0
    retention_class: RetentionClass
    created: str
    expires_at: str
    reviewer: str | None = None
    review_note: str | None = None
    draft_case: JsonValue = None


class DeletionEvidence(_Model):
    sample_id: str
    actor: str
    deleted_at: str
    reason: str


def is_expired(candidate: OnlineSampleCandidate, now: datetime | None = None) -> bool:
    moment = now or datetime.now(UTC)
    return moment > datetime.fromisoformat(candidate.expires_at)


def can_promote_to_case(candidate: OnlineSampleCandidate) -> bool:
    """A quarantined sample can gain a draft case; promotion is always human."""

    return candidate.state in {SampleState.QUARANTINED, SampleState.REVIEWED}


def default_expiry(retention: RetentionClass, now: datetime, ttl_days: int | None = None) -> str:
    days = ttl_days if ttl_days is not None else DEFAULT_TTLS[retention]
    return (now + timedelta(days=days)).isoformat()
