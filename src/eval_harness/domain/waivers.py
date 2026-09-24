"""Scoped, expiring, non-hard waivers and their effect on a comparison."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from ..datasets.hashing import canonical_json, sha256_hex
from .gates import Comparison, GateDecision, GateReason, ReasonCode

__all__ = [
    "HARD_INVARIANT_REASONS",
    "MAX_EXPIRY_DAYS",
    "WAIVABLE_REASONS",
    "WAIVER_SCHEMA_VERSION",
    "Waiver",
    "WaiverDecision",
    "apply_waivers",
    "compute_waiver_hash",
    "decide_with_reasons",
    "validate_waiver",
]

WAIVER_SCHEMA_VERSION = "eval.waiver.v1"
MAX_EXPIRY_DAYS = 14

WAIVABLE_REASONS: frozenset[str] = frozenset(
    {
        ReasonCode.SEMANTIC_SAMPLE_INSUFFICIENT.value,
        ReasonCode.SEMANTIC_INCONCLUSIVE.value,
        ReasonCode.JUDGE_UNAVAILABLE.value,
        ReasonCode.JUDGE_UNCALIBRATED.value,
        ReasonCode.BUDGET_LATENCY.value,
        ReasonCode.BUDGET_COST.value,
    }
)

HARD_INVARIANT_REASONS: frozenset[str] = frozenset(
    {
        ReasonCode.HARD_INVARIANT_SCHEMA.value,
        ReasonCode.HARD_INVARIANT_FORBIDDEN_TOOL.value,
        ReasonCode.HARD_INVARIANT_CITATION_IDENTITY.value,
        ReasonCode.HARD_INVARIANT_EVIDENCE_BOUNDARY.value,
        ReasonCode.HARD_INVARIANT_SECRET_DISCLOSURE.value,
        ReasonCode.INTEGRITY_FAILURE.value,
        ReasonCode.BASELINE_UNTRUSTED.value,
        ReasonCode.BASELINE_INCOMPATIBLE.value,
        ReasonCode.PROVENANCE_INCOMPLETE.value,
        ReasonCode.RUN_INCOMPLETE.value,
        ReasonCode.FLOOR_OVERALL.value,
        ReasonCode.FLOOR_PROFILE.value,
        ReasonCode.FLOOR_SAFETY.value,
        ReasonCode.FLOOR_CONTRACT.value,
        ReasonCode.REGRESSION_TOTAL_PASSED.value,
        ReasonCode.REGRESSION_PROFILE_PASSED.value,
        ReasonCode.REGRESSION_DETERMINISTIC_CASE.value,
        ReasonCode.SEMANTIC_LCB_FAIL.value,
    }
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Waiver(_Model):
    schema_version: str = WAIVER_SCHEMA_VERSION
    waiver_id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    approver: str = Field(min_length=1)
    approval_evidence: tuple[str, ...] = ()
    suite: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    scope_reasons: tuple[str, ...] = ()
    scope_cases: tuple[str, ...] = ()
    compensating_control: str = Field(min_length=1)
    created: str
    expires_at: str
    waiver_hash: str = ""


class WaiverDecision(_Model):
    waiver_id: str
    accepted: bool
    failures: tuple[str, ...] = ()
    suppressed_reasons: tuple[str, ...] = ()


def compute_waiver_hash(waiver: Waiver) -> str:
    payload = waiver.model_dump(mode="json")
    payload.pop("waiver_hash", None)
    return sha256_hex(canonical_json(payload))


def decide_with_reasons(reasons: tuple[GateReason, ...]) -> GateDecision:
    if any(reason.decision is GateDecision.BLOCK for reason in reasons):
        return GateDecision.BLOCK
    if any(reason.decision is GateDecision.REVIEW_REQUIRED for reason in reasons):
        return GateDecision.REVIEW_REQUIRED
    return GateDecision.PASS


def validate_waiver(
    waiver: Waiver, comparison: Comparison, now: datetime | None = None
) -> WaiverDecision:
    moment = now or datetime.now(UTC)
    failures: list[str] = []

    if waiver.waiver_hash and waiver.waiver_hash != compute_waiver_hash(waiver):
        failures.append("integrity_mismatch")
    if waiver.suite != comparison.suite_name or waiver.channel != comparison.channel:
        failures.append("scope_mismatch")
    if not waiver.approval_evidence:
        failures.append("missing_github_approval")
    if not waiver.scope_reasons or "*" in waiver.scope_reasons or "*" in waiver.scope_cases:
        failures.append("overbroad")
    if set(waiver.scope_reasons) & HARD_INVARIANT_REASONS:
        failures.append("hard_invariant_not_waivable")

    present = {reason.code for reason in comparison.reasons}
    if waiver.scope_reasons and not set(waiver.scope_reasons) <= present:
        failures.append("scope_not_present")

    if waiver.scope_cases:
        known_cases = {transition.case_id for transition in comparison.transitions}
        if not set(waiver.scope_cases) <= known_cases:
            failures.append("case_scope_not_present")

    expires_at = datetime.fromisoformat(waiver.expires_at)
    created = datetime.fromisoformat(waiver.created)
    if moment > expires_at:
        failures.append("expired")
    if expires_at - created > timedelta(days=MAX_EXPIRY_DAYS):
        failures.append("expiry_too_long")

    accepted = not failures
    suppressed = tuple(sorted(set(waiver.scope_reasons) & WAIVABLE_REASONS)) if accepted else ()
    return WaiverDecision(
        waiver_id=waiver.waiver_id,
        accepted=accepted,
        failures=tuple(failures),
        suppressed_reasons=suppressed,
    )


def apply_waivers(
    comparison: Comparison,
    waivers: tuple[Waiver, ...],
    now: datetime | None = None,
) -> tuple[Comparison, tuple[WaiverDecision, ...]]:
    decisions = tuple(validate_waiver(waiver, comparison, now) for waiver in waivers)
    suppressed: set[str] = set()
    accepted_ids: list[str] = []
    for decision in decisions:
        if decision.accepted:
            suppressed.update(decision.suppressed_reasons)
            accepted_ids.append(decision.waiver_id)
    if not suppressed:
        return comparison, decisions

    remaining = tuple(reason for reason in comparison.reasons if reason.code not in suppressed)
    updated = comparison.model_copy(
        update={
            "reasons": remaining,
            "decision": decide_with_reasons(remaining),
            "accepted_waivers": tuple(accepted_ids),
        }
    )
    return updated, decisions
