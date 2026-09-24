"""Authentication, roles, and tenant derivation."""

from __future__ import annotations

import jwt
import pytest

from eval_harness.api_auth import (
    FakeTokenVerifier,
    HmacJwtVerifier,
    Principal,
    Role,
    require_role,
)
from eval_harness.errors import HarnessError

SECRET = "0123456789abcdef0123456789abcdef"


def _principal(roles: set[Role], actor: str = "alice", tenant: str = "t1") -> Principal:
    return Principal(actor=actor, roles=frozenset(roles), tenant=tenant)


def test_fake_verifier_returns_principal_and_rejects_unknown() -> None:
    verifier = FakeTokenVerifier({"good": _principal({Role.RUNNER})})
    assert verifier.verify("good").actor == "alice"
    with pytest.raises(HarnessError, match="invalid token"):
        verifier.verify("bad")


def test_hmac_jwt_verifier_derives_roles_and_tenant() -> None:
    token = jwt.encode(
        {"sub": "bob", "roles": ["reader", "quality_owner"], "tenant": "tenant-7"},
        SECRET,
        algorithm="HS256",
    )
    principal = HmacJwtVerifier(SECRET).verify(token)
    assert principal.actor == "bob"
    assert principal.tenant == "tenant-7"
    assert principal.roles == frozenset({Role.READER, Role.QUALITY_OWNER})


def test_hmac_jwt_rejects_bad_signature() -> None:
    token = jwt.encode(
        {"sub": "bob", "roles": ["reader"]},
        "fedcba9876543210fedcba9876543210",
        algorithm="HS256",
    )
    with pytest.raises(HarnessError):
        HmacJwtVerifier(SECRET).verify(token)


def test_hmac_jwt_rejects_unknown_role() -> None:
    token = jwt.encode({"sub": "bob", "roles": ["superuser"]}, SECRET, algorithm="HS256")
    with pytest.raises(HarnessError, match="unknown role"):
        HmacJwtVerifier(SECRET).verify(token)


def test_hmac_jwt_requires_subject() -> None:
    token = jwt.encode({"roles": ["reader"]}, SECRET, algorithm="HS256")
    with pytest.raises(HarnessError):
        HmacJwtVerifier(SECRET).verify(token)


def test_require_role_allows_and_denies() -> None:
    reader = _principal({Role.READER})
    require_role(reader, Role.READER, Role.RUNNER)
    with pytest.raises(HarnessError) as excinfo:
        require_role(reader, Role.QUALITY_OWNER)
    assert excinfo.value.code == "FORBIDDEN"


def test_roles_do_not_leak_between_principals() -> None:
    owner = _principal({Role.QUALITY_OWNER})
    reader = _principal({Role.READER}, actor="carol")
    assert owner.has(Role.QUALITY_OWNER)
    assert not reader.has(Role.QUALITY_OWNER)
