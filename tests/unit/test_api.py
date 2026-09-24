"""HTTP API: translation, authorization, idempotency, and CLI parity."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.api import create_app
from eval_harness.api_auth import FakeTokenVerifier, Principal, Role
from eval_harness.application.compare import CompareService
from eval_harness.application.online import InMemorySampleStore, OnlineSampler
from eval_harness.application.promote import PromotionService
from eval_harness.application.run import RunRequest
from eval_harness.domain.gates import GatePolicy

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"

TOKENS = {
    "reader": Principal(actor="reader-user", roles=frozenset({Role.READER}), tenant="t1"),
    "runner": Principal(actor="runner-user", roles=frozenset({Role.RUNNER}), tenant="t1"),
    "owner": Principal(actor="owner-user", roles=frozenset({Role.QUALITY_OWNER}), tenant="t1"),
    "admin": Principal(actor="admin-user", roles=frozenset({Role.SECURITY_ADMIN}), tenant="t1"),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(run_factory):
    service, config = run_factory()
    store = FilesystemArtifactStore(Path(config.artifact_root))
    app = create_app(
        store=store,
        run_service=service,
        compare_service=CompareService(store),
        promotion_service=PromotionService(store),
        verifier=FakeTokenVerifier(TOKENS),
        sampler=OnlineSampler(InMemorySampleStore()),
        policy=GatePolicy(),
        default_run_config=config,
    )
    return TestClient(app, raise_server_exceptions=False), service, config, store


def test_health_endpoints(client) -> None:
    test_client, _service, _config, _store = client
    assert test_client.get("/health/live").json() == {"status": "ok"}
    assert test_client.get("/health/ready").json()["artifacts"] is True


def test_missing_token_is_unauthenticated(client) -> None:
    test_client, _service, _config, _store = client
    response = test_client.get("/v1/runs/anything")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_reader_cannot_create_run(client) -> None:
    test_client, _service, _config, _store = client
    response = test_client.post(
        "/v1/runs",
        headers=_headers("reader"),
        json={"suite_path": str(GOLDEN_V1), "run_id": "api-guard"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_create_run_matches_service_and_is_idempotent(client) -> None:
    test_client, service, config, _store = client
    body = {"suite_path": str(GOLDEN_V1), "run_id": "api-parity"}
    first = test_client.post(
        "/v1/runs", headers={**_headers("runner"), "Idempotency-Key": "k1"}, json=body
    )
    assert first.status_code == 202
    payload = first.json()
    assert payload["summary"]["completed"] == 50

    # Same idempotency key returns the stored response without re-running.
    second = test_client.post(
        "/v1/runs", headers={**_headers("runner"), "Idempotency-Key": "k1"}, json=body
    )
    assert second.json() == payload

    # Direct service call produces the same aggregate result.
    direct = service.run(RunRequest(suite_path=GOLDEN_V1, config=config, run_id="direct-parity"))
    assert direct.summary.pass_rate == payload["summary"]["pass_rate"]
    assert direct.summary.state_counts == payload["summary"]["state_counts"]


def test_get_run_and_cases(client) -> None:
    test_client, _service, _config, _store = client
    test_client.post(
        "/v1/runs",
        headers=_headers("runner"),
        json={"suite_path": str(GOLDEN_V1), "run_id": "api-read"},
    )
    run = test_client.get("/v1/runs/api-read", headers=_headers("reader"))
    assert run.status_code == 200
    assert run.json()["summary"]["completed"] == 50
    cases = test_client.get("/v1/runs/api-read/cases?profile=rag", headers=_headers("reader"))
    assert cases.status_code == 200
    assert all(case["primary_profile"] == "rag" for case in cases.json()["cases"])


def test_compare_and_promote_flow(client) -> None:
    test_client, _service, _config, _store = client
    test_client.post(
        "/v1/runs",
        headers=_headers("runner"),
        json={"suite_path": str(GOLDEN_V1), "run_id": "api-base"},
    )
    promoted = test_client.post(
        "/v1/baselines/golden-v1/stable/promotions",
        headers=_headers("owner"),
        json={
            "run_id": "api-base",
            "reason": "initial",
            "approval_evidence": ["github:review/1"],
            "policy_path": "evaluation/configs/gate-policy-v1.json",
        },
    )
    assert promoted.status_code == 200
    assert promoted.json()["approver"] == "owner-user"  # server-derived actor

    compare = test_client.post(
        "/v1/comparisons",
        headers=_headers("reader"),
        json={"candidate_run_id": "api-base", "suite": "golden-v1", "channel": "stable"},
    )
    assert compare.status_code == 200
    assert compare.json()["decision"] == "PASS"


def test_promotion_requires_owner(client) -> None:
    test_client, _service, _config, _store = client
    test_client.post(
        "/v1/runs",
        headers=_headers("runner"),
        json={"suite_path": str(GOLDEN_V1), "run_id": "api-base-2"},
    )
    denied = test_client.post(
        "/v1/baselines/golden-v1/stable/promotions",
        headers=_headers("runner"),
        json={"run_id": "api-base-2", "reason": "x"},
    )
    assert denied.status_code == 403


def test_sample_lifecycle_and_roles(client) -> None:
    test_client, _service, _config, _store = client
    created = test_client.post(
        "/v1/samples",
        headers=_headers("runner"),
        json={
            "sample_id": "s1",
            "tenant": "t1",
            "consent": True,
            "classification": "public",
            "payload": {"text": "key sk-ABCDEFGHIJKLMNOP"},
        },
    )
    assert created.status_code == 201
    assert "sk-ABCDEFGHIJKLMNOP" not in str(created.json()["payload"])

    # Reader cannot read quarantined samples.
    assert test_client.get("/v1/samples", headers=_headers("reader")).status_code == 403
    owner_list = test_client.get("/v1/samples", headers=_headers("owner"))
    assert owner_list.status_code == 200

    reviewed = test_client.post(
        "/v1/samples/s1/review", headers=_headers("owner"), json={"accept": True, "note": "ok"}
    )
    assert reviewed.json()["state"] == "reviewed"
    assert (
        test_client.get("/v1/samples/s1/draft", headers=_headers("owner")).json()["draft"] is True
    )

    deleted = test_client.request(
        "DELETE",
        "/v1/samples/s1",
        headers=_headers("admin"),
        json={"reason": "subject request"},
    )
    assert deleted.status_code == 200
    assert deleted.json()["actor"] == "admin-user"


def test_sample_consent_required_maps_to_400(client) -> None:
    test_client, _service, _config, _store = client
    response = test_client.post(
        "/v1/samples",
        headers=_headers("runner"),
        json={"sample_id": "s2", "tenant": "t1", "consent": False, "classification": "public"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONSENT_REQUIRED"
