"""Online sample lifecycle: consent, redaction, quarantine, retention, deletion."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from eval_harness.application.online import InMemorySampleStore, OnlineSampler
from eval_harness.domain.online import RetentionClass, SampleState, redact_value
from eval_harness.errors import HarnessError

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _sampler(now: datetime = NOW, consent_required: bool = True) -> OnlineSampler:
    return OnlineSampler(InMemorySampleStore(), consent_required=consent_required, now=lambda: now)


def test_redaction_catalog_scrubs_tokens_and_canaries() -> None:
    from eval_harness.domain.online import RedactionCatalog

    catalog = RedactionCatalog()
    redacted, hits = redact_value(
        {"text": "Authorization: Bearer abc.def sk-ABCDEFGHIJKLMNOP CANARY-7f3a9"}, catalog
    )
    assert hits >= 3
    assert "CANARY-7f3a9" not in str(redacted)
    assert "sk-ABCDEFGHIJKLMNOP" not in str(redacted)


def test_submit_requires_consent() -> None:
    sampler = _sampler()
    with pytest.raises(HarnessError, match="consent"):
        sampler.submit(
            sample_id="s1", tenant="t", consent=False, classification="public", payload={}
        )


def test_submit_quarantines_and_redacts_before_persistence() -> None:
    sampler = _sampler()
    candidate = sampler.submit(
        sample_id="s1",
        tenant="t",
        consent=True,
        classification="public",
        payload={"prompt": "my key is sk-ABCDEFGHIJKLMNOP"},
    )
    assert candidate.state is SampleState.QUARANTINED
    assert candidate.redaction_hits >= 1
    assert "sk-ABCDEFGHIJKLMNOP" not in str(candidate.payload)


def test_sensitive_classification_uses_restricted_retention() -> None:
    sampler = _sampler()
    candidate = sampler.submit(
        sample_id="s1", tenant="t", consent=True, classification="sensitive", payload={}
    )
    assert candidate.retention_class is RetentionClass.QUARANTINE_RESTRICTED


def test_review_marks_reviewed_or_rejected() -> None:
    sampler = _sampler()
    sampler.submit(sample_id="s1", tenant="t", consent=True, classification="public", payload={})
    reviewed = sampler.review("s1", "reviewer", accept=True, note="looks good")
    assert reviewed.state is SampleState.REVIEWED
    assert reviewed.reviewer == "reviewer"
    rejected = sampler.review("s1", "reviewer", accept=False)
    assert rejected.state is SampleState.REJECTED


def test_expired_sample_cannot_be_reviewed() -> None:
    sampler = _sampler()
    sampler.submit(sample_id="s1", tenant="t", consent=True, classification="public", payload={})
    later = OnlineSampler(
        sampler._store,
        now=lambda: NOW + timedelta(days=40),
    )
    with pytest.raises(HarnessError, match="expired"):
        later.review("s1", "reviewer", accept=True)


def test_purge_expired_removes_samples() -> None:
    sampler = _sampler()
    sampler.submit(sample_id="s1", tenant="t", consent=True, classification="public", payload={})
    later = OnlineSampler(sampler._store, now=lambda: NOW + timedelta(days=40))
    assert later.purge_expired() == ("s1",)


def test_delete_returns_evidence() -> None:
    sampler = _sampler()
    sampler.submit(sample_id="s1", tenant="t", consent=True, classification="public", payload={})
    evidence = sampler.delete("s1", "security", "subject request")
    assert evidence.sample_id == "s1"
    assert evidence.actor == "security"
    assert evidence.reason == "subject request"


def test_draft_case_is_a_proposal_not_a_publication() -> None:
    sampler = _sampler()
    sampler.submit(sample_id="s1", tenant="t", consent=True, classification="public", payload={})
    draft = sampler.propose_draft_case("s1")
    assert draft["draft"] is True
    assert "Human review required" in str(draft["note"])


def test_public_list_only_exposes_quarantine() -> None:
    sampler = _sampler()
    sampler.submit(sample_id="s1", tenant="t", consent=True, classification="public", payload={})
    assert [candidate.sample_id for candidate in sampler.list()] == ["s1"]
