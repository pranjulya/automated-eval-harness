"""Fake and HTTP adapters must satisfy one normalized contract."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from eval_harness.adapters.targets import (
    FakeTargetAdapter,
    HttpTargetAdapter,
    TargetConfig,
    load_fake_responses,
)
from eval_harness.datasets import load_suite
from eval_harness.domain.outcomes import OutcomeStatus

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "evaluation" / "fixtures" / "fake-target-v1.json"
SUITE = REPO / "evaluation" / "datasets" / "golden-v1"
RESPONSES = json.loads(FIXTURE.read_text(encoding="utf-8"))

FAKE_CONFIG = TargetConfig(adapter="fake", model="fake-v1")
HTTP_CONFIG = TargetConfig(adapter="http", model="fake-v1", base_url="http://local.test")


@pytest.fixture
def fake_adapter() -> FakeTargetAdapter:
    return FakeTargetAdapter(load_fake_responses(FIXTURE))


@pytest.fixture
def http_adapter() -> Iterator[HttpTargetAdapter]:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        return httpx.Response(200, json=RESPONSES[payload["case_id"]])

    adapter = HttpTargetAdapter(httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        yield adapter
    finally:
        adapter.close()


@pytest.mark.parametrize("case_id", sorted(RESPONSES))
def test_fake_and_http_normalize_identically(
    case_id: str, fake_adapter: FakeTargetAdapter, http_adapter: HttpTargetAdapter
) -> None:
    case = load_suite(SUITE).by_id(case_id)
    fake_outcome = fake_adapter.invoke(case, FAKE_CONFIG).outcome
    http_outcome = http_adapter.invoke(case, HTTP_CONFIG).outcome
    assert fake_outcome == http_outcome
    assert fake_outcome.status is OutcomeStatus.OK


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (429, OutcomeStatus.RATE_LIMITED),
        (500, OutcomeStatus.TARGET_ERROR),
        (404, OutcomeStatus.TARGET_ERROR),
    ],
)
def test_http_status_mapping(status_code: int, expected: OutcomeStatus) -> None:
    adapter = HttpTargetAdapter(
        httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(status_code)))
    )
    case = load_suite(SUITE).by_id("text-001")
    assert adapter.invoke(case, HTTP_CONFIG).state is expected


def test_http_malformed_json() -> None:
    adapter = HttpTargetAdapter(
        httpx.Client(
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, content=b"not json"))
        )
    )
    case = load_suite(SUITE).by_id("text-001")
    assert adapter.invoke(case, HTTP_CONFIG).state is OutcomeStatus.MALFORMED_RESPONSE


def test_http_timeout_mapping() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    adapter = HttpTargetAdapter(httpx.Client(transport=httpx.MockTransport(handler)))
    case = load_suite(SUITE).by_id("text-001")
    assert adapter.invoke(case, HTTP_CONFIG).state is OutcomeStatus.TIMEOUT


def test_http_rejects_oversize_body() -> None:
    adapter = HttpTargetAdapter(
        httpx.Client(
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, content=b"x" * 2048))
        )
    )
    case = load_suite(SUITE).by_id("text-001")
    config = TargetConfig(
        adapter="http", model="fake-v1", base_url="http://local.test", max_response_bytes=64
    )
    result = adapter.invoke(case, config)
    assert result.state is OutcomeStatus.MALFORMED_RESPONSE


def test_http_identity_marks_nondeterminism() -> None:
    adapter = HttpTargetAdapter()
    identity = adapter.identity(
        TargetConfig(
            adapter="http",
            model="alias",
            base_url="http://local.test",
            externally_nondeterministic=True,
        )
    )
    assert identity.externally_nondeterministic is True
    assert identity.deterministic is False


def test_fake_identity_is_deterministic() -> None:
    identity = FakeTargetAdapter({}).identity(FAKE_CONFIG)
    assert identity.deterministic is True
    assert identity.adapter == "fake"
