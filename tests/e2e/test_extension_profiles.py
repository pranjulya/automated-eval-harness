"""End-to-end proof for structured, RAG, and tool-use profiles.

Runs all 32 complex-profile goldens through the shared runner and asserts each
diagnostic failure mode is attributed to a stable code, with no profile-specific
lifecycle. Fake and HTTP adapters must normalize identically.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.adapters.targets import FakeTargetAdapter, HttpTargetAdapter, TargetConfig
from eval_harness.application.compare import CompareService
from eval_harness.application.promote import PromotionService
from eval_harness.application.replay import ReplayService
from eval_harness.application.run import RunRequest
from eval_harness.datasets import load_suite
from eval_harness.domain.baselines import PromotionAuthorization
from eval_harness.domain.gates import GateDecision, GatePolicy
from eval_harness.evaluators import build_registry
from eval_harness.evaluators.schema_store import load_schema_resolver

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
FAKE_RESPONSES = REPO_ROOT / "evaluation" / "fixtures" / "fake-target-v1.json"
PROFILES = {"structured_output", "rag", "tool_use"}

ORDER_DOCUMENT = {
    "order": {
        "id": "A1",
        "total": 10.0,
        "status": "paid",
        "quantity": 2,
        "items": [{}, {}, {}],
    }
}


def _responses() -> dict:
    return json.loads(FAKE_RESPONSES.read_text(encoding="utf-8"))


def _run_case(run_factory, case_id: str, response: dict | None = None) -> dict:
    responses = _responses()
    if response is not None:
        responses[case_id] = response
    service, config = run_factory(adapter=FakeTargetAdapter(responses))
    outcome = service.run(
        RunRequest(
            suite_path=GOLDEN_V1,
            config=config,
            case_ids=(case_id,),
            run_id=f"case-{case_id}",
        )
    )
    store = FilesystemArtifactStore(Path(config.artifact_root))
    line = (store.run_dir(outcome.run_id) / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    return json.loads(line[0])


def _codes(case_result: dict) -> set[str]:
    return {finding["code"] for finding in case_result["findings"] if not finding["passed"]}


def test_all_complex_profiles_execute_and_pass(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    store = FilesystemArtifactStore(Path(config.artifact_root))
    cases = [
        json.loads(line)
        for line in (store.run_dir(outcome.run_id) / "cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    complex_cases = [case for case in cases if case["primary_profile"] in PROFILES]
    assert len(complex_cases) == 32
    assert all(case["state"] == "PASS" for case in complex_cases)


def test_report_has_profile_diagnostics(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    report = Path(outcome.report_path).read_text(encoding="utf-8")
    assert "## Profile diagnostics" in report
    assert "INFO_RECALL_AT_K" in report
    assert "INFO_MRR" in report


def _structured(**mutations: object) -> dict:
    document = json.loads(json.dumps(ORDER_DOCUMENT))
    order = document["order"]
    for key, value in mutations.items():
        if value is None:
            order.pop(key, None)
        else:
            order[key] = value
    return {"status": "ok", "structured": document, "text": json.dumps(document)}


def _rag(evidence: list[dict], citations: list[dict], text: str = "answer") -> dict:
    return {"status": "ok", "text": text, "evidence": evidence, "citations": citations}


CASE_FAILURE_MODES = {
    "struct-002": (_structured(total="ten"), "HARD_INVARIANT_SCHEMA"),
    "struct-003": (_structured(status="cancelled"), "HARD_INVARIANT_SCHEMA"),
    "struct-004": (_structured(surprise=True), "HARD_INVARIANT_SCHEMA"),
    "struct-005": (_structured(id=None), "HARD_INVARIANT_SCHEMA"),
    "struct-006": (_structured(quantity=20), "BUSINESS_ASSERTION_FAILED"),
    "struct-010": (_structured(items=[{}, {}]), "BUSINESS_ASSERTION_FAILED"),
    "struct-009": ({"status": "ok", "text": "no json"}, "HARD_INVARIANT_SCHEMA"),
    "rag-006": (
        _rag([{"document_id": "policy-v1", "evidence_id": "policy-p1", "rank": 1}], []),
        "RETRIEVAL_MISS",
    ),
    "rag-007": (
        _rag([{"document_id": "x", "evidence_id": "other", "rank": 1}], []),
        "CONTEXT_EVIDENCE_LOST",
    ),
    "rag-004": (
        _rag(
            [
                {"document_id": "policy-v1", "evidence_id": "policy-p1", "rank": 1},
                {"document_id": "handbook-v1", "evidence_id": "handbook-p1", "rank": 2},
            ],
            [{"claim_id": "c1", "evidence_ids": ["policy-p1"]}],
        ),
        "CITATION_INCOMPLETE",
    ),
    "rag-010": (
        {"status": "ok", "text": "The address is 1 Main St."},
        "NO_ANSWER_FALSE_POSITIVE",
    ),
    "rag-008": (
        _rag(
            [{"document_id": "policy-v1", "evidence_id": "policy-p1", "rank": 1}],
            [{"claim_id": "c1", "evidence_ids": ["ghost"]}],
        ),
        "HARD_INVARIANT_CITATION_IDENTITY",
    ),
    "rag-011": (
        _rag([{"document_id": "tenant-b-v1", "evidence_id": "tenant-b-p1", "rank": 1}], []),
        "HARD_INVARIANT_EVIDENCE_BOUNDARY",
    ),
    "tool-002": (
        {
            "status": "ok",
            "tool_calls": [
                {"name": "create_ticket", "arguments": {"title": "Refund", "priority": "high"}}
            ],
        },
        "TOOL_ARGUMENT_FAILED",
    ),
    "tool-006": (
        {
            "status": "ok",
            "tool_calls": [
                {"name": "search", "arguments": {}},
                {"name": "search", "arguments": {}},
            ],
        },
        "TOOL_LOOP",
    ),
    "tool-005": (
        {
            "status": "ok",
            "tool_calls": [
                {"name": "search", "arguments": {"q": "a"}},
                {"name": "search", "arguments": {"q": "b"}},
                {"name": "search", "arguments": {"q": "c"}},
            ],
        },
        "TOOL_LOOP",
    ),
    "tool-010": (
        {"status": "ok", "tool_calls": [{"name": "search", "arguments": {}}]},
        "TOOL_SELECTION_FAILED",
    ),
    "tool-008": (
        {"status": "ok", "tool_calls": [{"name": "delete_account", "arguments": {}}]},
        "HARD_INVARIANT_FORBIDDEN_TOOL",
    ),
}


@pytest.mark.parametrize(
    ("case_id", "response", "expected"),
    [(case_id, response, code) for case_id, (response, code) in CASE_FAILURE_MODES.items()],
    ids=list(CASE_FAILURE_MODES),
)
def test_profile_failure_modes_are_attributed(
    run_factory, case_id: str, response: dict, expected: str
) -> None:
    result = _run_case(run_factory, case_id, response)
    assert expected in _codes(result)
    assert result["state"] == "FAIL"


def test_forbidden_tool_is_hard_invariant(run_factory) -> None:
    result = _run_case(
        run_factory,
        "tool-008",
        {"status": "ok", "tool_calls": [{"name": "delete_account", "arguments": {}}]},
    )
    hard = [
        finding
        for finding in result["findings"]
        if finding["code"] == "HARD_INVARIANT_FORBIDDEN_TOOL"
    ]
    assert hard
    assert hard[0]["severity"] == "hard_invariant"


def test_structured_extra_field_is_hard_invariant(run_factory) -> None:
    result = _run_case(run_factory, "struct-004", _structured(surprise=True))
    hard = [f for f in result["findings"] if f["code"] == "HARD_INVARIANT_SCHEMA"]
    assert hard
    assert hard[0]["severity"] == "hard_invariant"


def test_fake_and_http_agree_for_all_complex_profiles() -> None:
    responses = _responses()
    fake = FakeTargetAdapter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        return httpx.Response(200, json=responses[payload["case_id"]])

    http = HttpTargetAdapter(httpx.Client(transport=httpx.MockTransport(handler)))
    fake_config = TargetConfig(adapter="fake", model="fake-v1")
    http_config = TargetConfig(adapter="http", model="fake-v1", base_url="http://local.test")
    suite = load_suite(GOLDEN_V1)
    complex_ids = [case.case_id for case in suite.cases if case.primary_profile.value in PROFILES]
    try:
        for case_id in complex_ids:
            case = suite.by_id(case_id)
            assert fake.invoke(case, fake_config).outcome == http.invoke(case, http_config).outcome
    finally:
        http.close()


def test_replay_and_compare_use_no_profile_specific_path(run_factory) -> None:
    service, config = run_factory()
    baseline = service.run(RunRequest(suite_path=GOLDEN_V1, config=config, run_id="ext-baseline"))
    store = FilesystemArtifactStore(Path(config.artifact_root))

    replayed = ReplayService(build_registry(load_schema_resolver(REPO_ROOT))).replay(
        store, baseline.run_id
    )
    assert replayed.summary.completed == 50

    candidate = service.run(RunRequest(suite_path=GOLDEN_V1, config=config, run_id="ext-candidate"))
    authorization = PromotionAuthorization(
        actor="owner", approval_evidence=("github:review/1",), reason="baseline"
    )
    PromotionService(store).promote(
        "ext-baseline", "golden-v1", "stable", authorization, GatePolicy().policy_hash()
    )
    comparison = CompareService(store).compare(
        candidate.run_id, "golden-v1", "stable", GatePolicy()
    )
    assert comparison.decision is GateDecision.PASS
