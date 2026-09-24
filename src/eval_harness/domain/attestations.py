"""Gate attestations that bind a decision to a commit and artifact hashes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict

from ..datasets.hashing import canonical_json, sha256_hex
from .gates import GateDecision

__all__ = [
    "ATTESTATION_SCHEMA_VERSION",
    "DEFAULT_TTL_HOURS",
    "AttestationVerification",
    "GateAttestation",
    "build_attestation",
    "compute_attestation_hash",
    "verify_attestation",
]

ATTESTATION_SCHEMA_VERSION = "eval.attestation.v1"
DEFAULT_TTL_HOURS = 24


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GateAttestation(_Model):
    schema_version: str = ATTESTATION_SCHEMA_VERSION
    commit: str
    run_id: str
    run_manifest_hash: str
    baseline_hash: str
    workflow: str
    decision: GateDecision
    reason_codes: tuple[str, ...] = ()
    created: str
    expires_at: str
    attestation_hash: str = ""


class AttestationVerification(_Model):
    ok: bool
    failures: tuple[str, ...] = ()


def compute_attestation_hash(attestation: GateAttestation) -> str:
    payload = attestation.model_dump(mode="json")
    payload.pop("attestation_hash", None)
    return sha256_hex(canonical_json(payload))


def build_attestation(
    *,
    commit: str,
    run_id: str,
    run_manifest_hash: str,
    baseline_hash: str,
    workflow: str,
    decision: GateDecision,
    reason_codes: tuple[str, ...] = (),
    now: datetime | None = None,
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> GateAttestation:
    created = now or datetime.now(UTC)
    attestation = GateAttestation(
        commit=commit,
        run_id=run_id,
        run_manifest_hash=run_manifest_hash,
        baseline_hash=baseline_hash,
        workflow=workflow,
        decision=decision,
        reason_codes=reason_codes,
        created=created.isoformat(),
        expires_at=(created + timedelta(hours=ttl_hours)).isoformat(),
    )
    return attestation.model_copy(
        update={"attestation_hash": compute_attestation_hash(attestation)}
    )


def verify_attestation(
    attestation: GateAttestation,
    *,
    now: datetime | None = None,
    expected_commit: str | None = None,
    expected_run_manifest_hash: str | None = None,
    expected_baseline_hash: str | None = None,
    allow_expired: bool = False,
    require_pass: bool = True,
) -> AttestationVerification:
    failures: list[str] = []
    if attestation.attestation_hash != compute_attestation_hash(attestation):
        failures.append("hash_mismatch")
    if require_pass and attestation.decision is not GateDecision.PASS:
        failures.append("decision_not_pass")
    if expected_commit is not None and attestation.commit != expected_commit:
        failures.append("stale_commit")
    if (
        expected_run_manifest_hash is not None
        and attestation.run_manifest_hash != expected_run_manifest_hash
    ):
        failures.append("wrong_run_manifest")
    if expected_baseline_hash is not None and attestation.baseline_hash != expected_baseline_hash:
        failures.append("wrong_baseline")
    if not allow_expired:
        moment = now or datetime.now(UTC)
        if moment > datetime.fromisoformat(attestation.expires_at):
            failures.append("expired")
    return AttestationVerification(ok=not failures, failures=tuple(failures))
