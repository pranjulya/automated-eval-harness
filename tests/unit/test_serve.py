"""`serve` wiring and `dev-token`: same services as the CLI, fail-closed auth."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from eval_harness.api_auth import HmacJwtVerifier, Role, issue_hs256_token
from eval_harness.cli import build_service_app, main
from eval_harness.config import JWT_SECRET_ENV, AppConfig, load_config
from eval_harness.errors import ConfigError, ExitCode

REPO_ROOT = Path(__file__).resolve().parents[2]
FAKE_CONFIG = REPO_ROOT / "evaluation" / "configs" / "fake.json"
POLICY = REPO_ROOT / "evaluation" / "configs" / "gate-policy-v1.json"
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
SECRET = "s" * 32


def test_jwt_secret_env_is_a_known_key(tmp_path: Path) -> None:
    config = load_config({JWT_SECRET_ENV: SECRET}, base_dir=tmp_path)
    assert SECRET not in config.model_dump_json()


def test_issued_token_round_trips_through_verifier() -> None:
    token = issue_hs256_token(SECRET, actor="alice", roles=[Role.RUNNER], tenant="t1")
    principal = HmacJwtVerifier(SECRET).verify(token)
    assert principal.actor == "alice"
    assert principal.roles == frozenset({Role.RUNNER})
    assert principal.tenant == "t1"


def test_served_app_runs_suite_with_real_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    config = AppConfig(artifact_root=tmp_path / "artifacts")
    app, adapter = build_service_app(config, FAKE_CONFIG, POLICY, SECRET)
    client = TestClient(app)
    runner = issue_hs256_token(SECRET, actor="ci", roles=[Role.RUNNER])
    reader = issue_hs256_token(SECRET, actor="viewer", roles=[Role.READER])

    assert client.get("/health/ready").json()["artifacts"] is True
    assert client.get("/v1/runs/x", headers={"Authorization": "Bearer bogus"}).status_code == 401

    created = client.post(
        "/v1/runs",
        headers={"Authorization": f"Bearer {runner}"},
        json={"suite_path": str(GOLDEN_V1), "run_id": "served-1"},
    )
    assert created.status_code == 202, created.text
    assert created.json()["summary"]["completed"] == 50

    fetched = client.get("/v1/runs/served-1", headers={"Authorization": f"Bearer {reader}"})
    assert fetched.status_code == 200
    assert (tmp_path / "artifacts" / "runs" / "served-1").is_dir()
    adapter_close = getattr(adapter, "close", None)
    if callable(adapter_close):
        adapter_close()


def test_serve_refuses_short_or_missing_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EVAL_HARNESS_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv(JWT_SECRET_ENV, "too-short")
    code = main(["serve", "--config", str(FAKE_CONFIG), "--policy", str(POLICY)])
    assert code == int(ConfigError("x").exit_code)
    err = capsys.readouterr().err
    assert JWT_SECRET_ENV in err
    assert "too-short" not in err


def test_dev_token_prints_verifiable_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EVAL_HARNESS_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv(JWT_SECRET_ENV, SECRET)
    code = main(["dev-token", "--actor", "bob", "--role", "reader", "--role", "runner"])
    assert code == int(ExitCode.SUCCESS)
    principal = HmacJwtVerifier(SECRET).verify(capsys.readouterr().out.strip())
    assert principal.roles == frozenset({Role.READER, Role.RUNNER})


def test_dev_token_refused_in_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EVAL_HARNESS_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("EVAL_HARNESS_ENVIRONMENT", "production")
    monkeypatch.setenv(JWT_SECRET_ENV, SECRET)
    code = main(["dev-token", "--actor", "bob", "--role", "reader"])
    assert code != int(ExitCode.SUCCESS)
    assert capsys.readouterr().out == ""
