"""Authentication, roles, and tenant scoping for the HTTP service.

The server derives actor and roles from the verified token, never from the
request body. Local/CI default is HS256 with a shared secret; deployments point
at a real OIDC issuer/JWKS.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Protocol, runtime_checkable

import jwt
from pydantic import BaseModel, ConfigDict

from .errors import HarnessError

__all__ = [
    "FakeTokenVerifier",
    "HmacJwtVerifier",
    "Principal",
    "Role",
    "TokenVerifier",
    "require_role",
]


class Role(StrEnum):
    READER = "reader"
    RUNNER = "runner"
    QUALITY_OWNER = "quality_owner"
    SECURITY_ADMIN = "security_admin"


class Principal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor: str
    roles: frozenset[Role]
    tenant: str = "default"

    def has(self, *roles: Role) -> bool:
        return bool(self.roles & set(roles))


@runtime_checkable
class TokenVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class FakeTokenVerifier:
    """Deterministic verifier for tests and local development."""

    def __init__(self, tokens: Mapping[str, Principal]) -> None:
        self._tokens = dict(tokens)

    def verify(self, token: str) -> Principal:
        principal = self._tokens.get(token)
        if principal is None:
            raise HarnessError("invalid token", code="UNAUTHENTICATED")
        return principal


class HmacJwtVerifier:
    """Verify an HS256 JWT and derive actor/roles/tenant from its claims."""

    def __init__(
        self, secret: str, *, issuer: str | None = None, audience: str | None = None
    ) -> None:
        self._secret = secret
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub"]},
            )
        except jwt.PyJWTError as error:
            raise HarnessError("invalid token", code="UNAUTHENTICATED") from error
        roles = claims.get("roles", [])
        try:
            parsed = frozenset(Role(role) for role in roles)
        except ValueError as error:
            raise HarnessError("token has an unknown role", code="UNAUTHENTICATED") from error
        return Principal(
            actor=str(claims["sub"]),
            roles=parsed,
            tenant=str(claims.get("tenant", "default")),
        )


def require_role(principal: Principal, *roles: Role) -> None:
    if not principal.has(*roles):
        raise HarnessError(
            "role is not authorized for this action",
            code="FORBIDDEN",
            details={"required": [role.value for role in roles]},
        )
