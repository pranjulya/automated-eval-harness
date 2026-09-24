"""Judge adapter contract tests (fake and HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from eval_harness.adapters.judges import (
    FakeJudgeAdapter,
    HttpJudgeAdapter,
    JudgeConfig,
    RawJudgeResponse,
)
from eval_harness.domain.judging import JudgeRequest, Rubric, SemanticDimension
from eval_harness.errors import JudgeInvalidError, JudgeUnavailableError

REPO_ROOT = Path(__file__).resolve().parents[3]
RUBRIC = Rubric.model_validate_json(
    (REPO_ROOT / "evaluation" / "rubrics" / "relevance-v1.json").read_text(encoding="utf-8")
)
CONFIG = JudgeConfig(provider="http", model="judge-v1", auth_header_env="JUDGE_TOKEN")


def _request(case_id: str = "text-777") -> JudgeRequest:
    return JudgeRequest(
        case_id=case_id,
        rubric_id=RUBRIC.rubric_id,
        rubric_version=RUBRIC.version,
        dimension=SemanticDimension.RELEVANCE,
        prompt_hash=RUBRIC.prompt_hash,
        candidate_text="the candidate answer",
    )


def test_fake_judge_returns_raw_response() -> None:
    adapter = FakeJudgeAdapter({"relevance-v1|text-777": {"ordinal": 5, "rationale": "ok"}})
    response = adapter.judge(_request(), CONFIG)
    assert response == RawJudgeResponse(ordinal=5, rationale="ok")
    assert adapter.adapter_id == "fake-judge"


def test_fake_judge_missing_key_is_unavailable() -> None:
    with pytest.raises(JudgeUnavailableError):
        FakeJudgeAdapter({}).judge(_request(), CONFIG)


def test_fake_judge_invalid_entry_is_invalid() -> None:
    adapter = FakeJudgeAdapter({"relevance-v1|text-777": {"ordinal": 9}})
    with pytest.raises(JudgeInvalidError):
        adapter.judge(_request(), CONFIG)


@pytest.fixture
def http_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_HARNESS_JUDGE_URL", "http://judge.test")
    monkeypatch.setenv("JUDGE_TOKEN", "super-secret")


def test_http_judge_parses_strict_output(http_env: None) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ordinal": 4, "evidence_ids": ["e1"], "rationale": "ok"})

    with HttpJudgeAdapter(httpx.Client(transport=httpx.MockTransport(handler))) as adapter:
        response = adapter.judge(_request(), CONFIG)
    assert response.ordinal == 4
    assert response.evidence_ids == ("e1",)


def test_http_judge_5xx_is_unavailable(http_env: None) -> None:
    adapter = HttpJudgeAdapter(
        httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(500)))
    )
    with pytest.raises(JudgeUnavailableError):
        adapter.judge(_request(), CONFIG)
    adapter.close()


def test_http_judge_malformed_is_invalid(http_env: None) -> None:
    adapter = HttpJudgeAdapter(
        httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200, content=b"nope")))
    )
    with pytest.raises(JudgeInvalidError):
        adapter.judge(_request(), CONFIG)
    adapter.close()


def test_http_judge_oversize_is_invalid(http_env: None) -> None:
    adapter = HttpJudgeAdapter(
        httpx.Client(
            transport=httpx.MockTransport(lambda _r: httpx.Response(200, content=b"x" * 2048))
        )
    )
    with pytest.raises(JudgeInvalidError):
        adapter.judge(_request(), CONFIG)
    adapter.close()


def test_http_judge_missing_secret_is_unavailable(
    http_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("JUDGE_TOKEN")
    with (
        HttpJudgeAdapter(
            httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200)))
        ) as adapter,
        pytest.raises(JudgeUnavailableError),
    ):
        adapter.judge(_request(), CONFIG)


def test_http_judge_secret_is_not_echoed(http_env: None) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization", "")
        return httpx.Response(500)

    adapter = HttpJudgeAdapter(httpx.Client(transport=httpx.MockTransport(handler)))
    with adapter, pytest.raises(JudgeUnavailableError) as excinfo:
        adapter.judge(_request(), CONFIG)
    assert (
        json.dumps({"message": excinfo.value.message, "details": excinfo.value.details}).find(
            "super-secret"
        )
        == -1
    )
