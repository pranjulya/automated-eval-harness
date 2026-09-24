"""Online sampling application service.

Redaction happens before persistence; samples are quarantined and advanced only
by explicit human review. Nothing here can publish a dataset, rubric,
threshold, or baseline.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from ..domain.online import (
    DEFAULT_TTLS,
    DeletionEvidence,
    OnlineSampleCandidate,
    RedactionCatalog,
    RetentionClass,
    SampleState,
    can_promote_to_case,
    default_expiry,
    is_expired,
    redact_value,
)
from ..errors import HarnessError

__all__ = ["InMemorySampleStore", "OnlineSampler", "SampleStore"]


class SampleStore(Protocol):
    def save(self, candidate: OnlineSampleCandidate) -> None: ...
    def get(self, sample_id: str) -> OnlineSampleCandidate: ...
    def list(self) -> tuple[OnlineSampleCandidate, ...]: ...
    def delete(self, sample_id: str) -> None: ...


class InMemorySampleStore:
    def __init__(self) -> None:
        self._items: dict[str, OnlineSampleCandidate] = {}

    def save(self, candidate: OnlineSampleCandidate) -> None:
        self._items[candidate.sample_id] = candidate

    def get(self, sample_id: str) -> OnlineSampleCandidate:
        candidate = self._items.get(sample_id)
        if candidate is None:
            raise HarnessError(
                "sample not found", code="SAMPLE_NOT_FOUND", details={"sample_id": sample_id}
            )
        return candidate

    def list(self) -> tuple[OnlineSampleCandidate, ...]:
        return tuple(self._items[key] for key in sorted(self._items))

    def delete(self, sample_id: str) -> None:
        self._items.pop(sample_id, None)


class OnlineSampler:
    def __init__(
        self,
        store: SampleStore,
        *,
        catalog: RedactionCatalog | None = None,
        consent_required: bool = True,
        ttls: dict[RetentionClass, int] | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._store = store
        self._catalog = catalog or RedactionCatalog()
        self._consent_required = consent_required
        self._ttls = ttls or DEFAULT_TTLS
        self._now = now

    def submit(
        self,
        *,
        sample_id: str,
        tenant: str,
        consent: bool,
        classification: str,
        payload: object,
    ) -> OnlineSampleCandidate:
        if self._consent_required and not consent:
            raise HarnessError(
                "online sampling requires explicit consent",
                code="CONSENT_REQUIRED",
                details={"sample_id": sample_id},
            )
        redacted, hits = redact_value(payload, self._catalog)  # type: ignore[arg-type]
        retention = (
            RetentionClass.QUARANTINE_RESTRICTED
            if classification in {"sensitive", "restricted"}
            else RetentionClass.ONLINE_SHORT
        )
        moment = self._now()
        candidate = OnlineSampleCandidate(
            sample_id=sample_id,
            tenant=tenant,
            consent=consent,
            classification=classification,
            state=SampleState.QUARANTINED,
            payload=redacted,
            redaction_hits=hits,
            retention_class=retention,
            created=moment.isoformat(),
            expires_at=default_expiry(retention, moment, self._ttls.get(retention)),
        )
        self._store.save(candidate)
        return candidate

    def list(self) -> tuple[OnlineSampleCandidate, ...]:
        return self._store.list()

    def review(
        self, sample_id: str, reviewer: str, *, accept: bool, note: str = ""
    ) -> OnlineSampleCandidate:
        candidate = self._store.get(sample_id)
        if is_expired(candidate, self._now()):
            raise HarnessError(
                "sample has expired", code="SAMPLE_EXPIRED", details={"sample_id": sample_id}
            )
        updated = candidate.model_copy(
            update={
                "state": SampleState.REVIEWED if accept else SampleState.REJECTED,
                "reviewer": reviewer,
                "review_note": note,
            }
        )
        self._store.save(updated)
        return updated

    def delete(self, sample_id: str, actor: str, reason: str) -> DeletionEvidence:
        candidate = self._store.get(sample_id)
        evidence = DeletionEvidence(
            sample_id=candidate.sample_id,
            actor=actor,
            deleted_at=self._now().isoformat(),
            reason=reason,
        )
        self._store.delete(sample_id)
        return evidence

    def purge_expired(self) -> tuple[str, ...]:
        moment = self._now()
        purged = [
            candidate.sample_id for candidate in self._store.list() if is_expired(candidate, moment)
        ]
        for sample_id in purged:
            self._store.delete(sample_id)
        return tuple(purged)

    def propose_draft_case(self, sample_id: str) -> dict[str, object]:
        """Return a redacted draft case. This is a proposal, never a publication."""

        candidate = self._store.get(sample_id)
        if not can_promote_to_case(candidate):
            raise HarnessError(
                "sample is not eligible for a draft case",
                code="SAMPLE_NOT_ELIGIBLE",
                details={"sample_id": sample_id, "state": str(candidate.state)},
            )
        return {
            "draft": True,
            "source_sample_id": candidate.sample_id,
            "classification": candidate.classification,
            "payload": candidate.payload,
            "note": "Human review required before this can enter a golden suite.",
        }
