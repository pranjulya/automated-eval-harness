"""HTTP target adapter integration tests against a local test server."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from eval_harness.adapters.targets import HttpTargetAdapter, TargetConfig
from eval_harness.datasets import load_suite
from eval_harness.domain.outcomes import OutcomeStatus

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "evaluation" / "datasets" / "golden-v1"
RESPONSES = json.loads(
    (REPO / "evaluation" / "fixtures" / "fake-target-v1.json").read_text(encoding="utf-8")
)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # silence test server
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", 0))
        self.rfile.read(length)
        path = self.path
        if path == "/force-429":
            self._send(429, b"rate limited")
            return
        if path == "/force-500":
            self._send(500, b"boom")
            return
        if path == "/require-auth":
            if not self.headers.get("authorization"):
                self._send(401, b"unauthorized")
                return
            self._send(200, json.dumps(RESPONSES["text-001"]).encode())
            return
        if path == "/force-bad-json":
            self._send(200, b"not json")
            return
        if path == "/force-huge":
            self._send(200, b"x" * 100_000)
            return
        if path == "/force-slow":
            time.sleep(0.5)
            self._send(200, json.dumps(RESPONSES["text-001"]).encode())
            return
        self._send(200, json.dumps(RESPONSES["text-001"]).encode())

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def base_url() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def adapter() -> Iterator[HttpTargetAdapter]:
    instance = HttpTargetAdapter()
    try:
        yield instance
    finally:
        instance.close()


def _config(base_url: str, path: str = "/invoke", **overrides: object) -> TargetConfig:
    payload: dict[str, object] = {
        "adapter": "http",
        "model": "local-http",
        "base_url": base_url,
        "path": path,
    }
    payload.update(overrides)
    return TargetConfig.model_validate(payload)


def test_ok_response_matches_fixture(base_url: str, adapter: HttpTargetAdapter) -> None:
    case = load_suite(SUITE).by_id("text-001")
    result = adapter.invoke(case, _config(base_url))
    assert result.state is OutcomeStatus.OK
    assert result.outcome.text == RESPONSES["text-001"]["text"]
    assert result.http_status == 200


def test_rate_limited(base_url: str, adapter: HttpTargetAdapter) -> None:
    case = load_suite(SUITE).by_id("text-001")
    assert adapter.invoke(case, _config(base_url, "/force-429")).state is OutcomeStatus.RATE_LIMITED


def test_server_error(base_url: str, adapter: HttpTargetAdapter) -> None:
    case = load_suite(SUITE).by_id("text-001")
    assert adapter.invoke(case, _config(base_url, "/force-500")).state is OutcomeStatus.TARGET_ERROR


def test_malformed_json(base_url: str, adapter: HttpTargetAdapter) -> None:
    case = load_suite(SUITE).by_id("text-001")
    assert (
        adapter.invoke(case, _config(base_url, "/force-bad-json")).state
        is OutcomeStatus.MALFORMED_RESPONSE
    )


def test_oversize_body_rejected(base_url: str, adapter: HttpTargetAdapter) -> None:
    case = load_suite(SUITE).by_id("text-001")
    result = adapter.invoke(case, _config(base_url, "/force-huge", max_response_bytes=64))
    assert result.state is OutcomeStatus.MALFORMED_RESPONSE


def test_read_timeout(base_url: str, adapter: HttpTargetAdapter) -> None:
    case = load_suite(SUITE).by_id("text-001")
    result = adapter.invoke(case, _config(base_url, "/force-slow", timeout_ms=50))
    assert result.state is OutcomeStatus.TIMEOUT


def test_missing_secret_reference_fails_closed(base_url: str, adapter: HttpTargetAdapter) -> None:
    case = load_suite(SUITE).by_id("text-001")
    result = adapter.invoke(case, _config(base_url, auth_header_env="MISSING_SECRET_ENV"))
    assert result.state is OutcomeStatus.TARGET_ERROR
    assert result.error == "secret reference is not set"


def test_secret_is_sent_but_never_echoed(
    base_url: str, adapter: HttpTargetAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TARGET_TEST_TOKEN", "super-secret-token")
    case = load_suite(SUITE).by_id("text-001")
    result = adapter.invoke(
        case, _config(base_url, "/require-auth", auth_header_env="TARGET_TEST_TOKEN")
    )
    assert result.state is OutcomeStatus.OK
    assert result.error is None
    assert "super-secret-token" not in json.dumps(
        {"error": result.error, "request_hash": result.request_hash}
    )
