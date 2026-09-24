"""Generic HTTP judge adapter with bounded size/time and secret references."""

from __future__ import annotations

import os

import httpx
from pydantic import ValidationError

from ...domain.judging import JudgeRequest
from ...errors import JudgeInvalidError, JudgeUnavailableError
from .base import JudgeAdapter, JudgeConfig, RawJudgeResponse

__all__ = ["HttpJudgeAdapter"]


class HttpJudgeAdapter(JudgeAdapter):
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()
        self._owns_client = client is None

    @property
    def adapter_id(self) -> str:
        return "http-judge"

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpJudgeAdapter:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def judge(self, request: JudgeRequest, config: JudgeConfig) -> RawJudgeResponse:
        if config.auth_header_env is None:
            raise JudgeUnavailableError("judge provider requires an auth secret reference")
        token = os.environ.get(config.auth_header_env)
        if not token:
            raise JudgeUnavailableError("judge secret reference is not set")
        base = os.environ.get("EVAL_HARNESS_JUDGE_URL")
        if not base:
            raise JudgeUnavailableError("judge URL is not configured")
        try:
            response = self._client.post(
                f"{base}/judge",
                json=request.model_dump(mode="json"),
                headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
                timeout=config.timeout_ms / 1000,
            )
        except httpx.TimeoutException as error:
            raise JudgeUnavailableError("judge request timed out") from error
        except httpx.TransportError as error:
            raise JudgeUnavailableError("judge transport failure") from error
        if response.status_code == 429 or response.status_code >= 500:
            raise JudgeUnavailableError("judge provider unavailable")
        if len(response.content) > config.max_response_bytes:
            raise JudgeInvalidError("judge response too large")
        try:
            payload = response.json()
        except ValueError as error:
            raise JudgeInvalidError("judge response is not JSON") from error
        if not isinstance(payload, dict):
            raise JudgeInvalidError("judge response must be a JSON object")
        try:
            return RawJudgeResponse.model_validate(payload)
        except ValidationError as error:
            raise JudgeInvalidError("judge response violates the contract") from error
