"""Generic HTTP target adapter with bounded size/time and secret references."""

from __future__ import annotations

import os

import httpx
from pydantic import ValidationError

from ...datasets.hashing import canonical_json, sha256_hex
from ...domain.cases import EvalCase
from ...domain.outcomes import NormalizedOutcome, OutcomeStatus
from .base import AttemptResult, TargetAdapter, TargetConfig, TargetIdentity

__all__ = ["HttpTargetAdapter"]


class HttpTargetAdapter(TargetAdapter):
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()
        self._owns_client = client is None

    @property
    def adapter_id(self) -> str:
        return "http"

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpTargetAdapter:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def identity(self, config: TargetConfig) -> TargetIdentity:
        endpoint = f"{config.base_url or ''}{config.path}"
        return TargetIdentity(
            adapter="http",
            adapter_version=config.adapter_version,
            endpoint_id=endpoint,
            request_template_hash=config.request_template_hash,
            model=config.model,
            deterministic=not config.externally_nondeterministic,
            seed_supported=config.seed_supported,
            externally_nondeterministic=config.externally_nondeterministic,
        )

    def invoke(self, case: EvalCase, config: TargetConfig) -> AttemptResult:
        if config.base_url is None:
            return self._failure(case, config, OutcomeStatus.TARGET_ERROR, "base_url is required")
        payload = {
            "case_id": case.case_id,
            "model": config.model,
            "input": case.input.model_dump(mode="json"),
        }
        request_hash = sha256_hex(canonical_json(payload))
        headers = {"content-type": "application/json"}
        if config.auth_header_env is not None:
            token = os.environ.get(config.auth_header_env)
            if not token:
                return self._failure(
                    case,
                    config,
                    OutcomeStatus.TARGET_ERROR,
                    "secret reference is not set",
                    request_hash=request_hash,
                )
            headers["authorization"] = f"Bearer {token}"
        url = f"{config.base_url}{config.path}"
        try:
            response = self._client.post(
                url, json=payload, headers=headers, timeout=config.timeout_ms / 1000
            )
        except httpx.TimeoutException:
            return self._failure(
                case, config, OutcomeStatus.TIMEOUT, "request timed out", request_hash=request_hash
            )
        except httpx.TransportError:
            return self._failure(
                case,
                config,
                OutcomeStatus.TRANSPORT_ERROR,
                "transport failure",
                request_hash=request_hash,
            )
        if len(response.content) > config.max_response_bytes:
            return self._failure(
                case,
                config,
                OutcomeStatus.MALFORMED_RESPONSE,
                "response too large",
                request_hash=request_hash,
                http_status=response.status_code,
            )
        if response.status_code == 429:
            return self._failure(
                case,
                config,
                OutcomeStatus.RATE_LIMITED,
                "rate limited",
                request_hash=request_hash,
                http_status=429,
            )
        if response.status_code >= 400:
            return self._failure(
                case,
                config,
                OutcomeStatus.TARGET_ERROR,
                "target returned an error status",
                request_hash=request_hash,
                http_status=response.status_code,
            )
        try:
            data = response.json()
        except ValueError:
            return self._failure(
                case,
                config,
                OutcomeStatus.MALFORMED_RESPONSE,
                "response is not JSON",
                request_hash=request_hash,
                http_status=response.status_code,
            )
        if not isinstance(data, dict):
            return self._failure(
                case,
                config,
                OutcomeStatus.MALFORMED_RESPONSE,
                "response must be a JSON object",
                request_hash=request_hash,
                http_status=response.status_code,
            )
        try:
            outcome = NormalizedOutcome.model_validate({**data, "status": "ok"})
        except ValidationError:
            return self._failure(
                case,
                config,
                OutcomeStatus.MALFORMED_RESPONSE,
                "response schema invalid",
                request_hash=request_hash,
                http_status=response.status_code,
            )
        return AttemptResult(
            state=OutcomeStatus.OK,
            outcome=outcome,
            attempt_index=1,
            request_hash=request_hash,
            http_status=response.status_code,
            response_hash=sha256_hex(response.content),
        )

    def _failure(
        self,
        case: EvalCase,
        config: TargetConfig,
        state: OutcomeStatus,
        message: str,
        *,
        request_hash: str | None = None,
        http_status: int | None = None,
    ) -> AttemptResult:
        del case, config
        outcome = NormalizedOutcome(status=state)
        return AttemptResult(
            state=state,
            outcome=outcome,
            attempt_index=1,
            request_hash=request_hash or sha256_hex(canonical_json({"case_id": "<unknown>"})),
            http_status=http_status,
            error=message,
        )
