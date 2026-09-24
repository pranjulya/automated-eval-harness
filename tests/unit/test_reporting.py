"""Report projection tests, including untrusted-text escaping."""

from __future__ import annotations

from pathlib import Path

from eval_harness.application.aggregate import aggregate
from eval_harness.datasets import load_suite
from eval_harness.domain.findings import CaseState
from eval_harness.domain.runs import (
    CaseResult,
    CodeIdentity,
    DatasetRef,
    RunManifest,
    RunStatus,
)
from eval_harness.reporting.json_report import summary_payload
from eval_harness.reporting.markdown import escape, render_report


def _manifest(dataset_name: str = "golden-v1", commit: str = "abc123") -> RunManifest:
    return RunManifest(
        run_id="run-1",
        status=RunStatus.COMPLETED,
        started_at="2026-09-10T00:00:00Z",
        finished_at="2026-09-10T00:00:01Z",
        command="run",
        dataset=DatasetRef(
            name=dataset_name,
            suite_version="1.0.1",
            schema_version="eval.case.v1",
            content_hash="hash",
            case_ids=("text-001",),
        ),
        target={"adapter": "fake", "model": "fake-v1"},
        evaluator_version="evaluators.v1",
        retry_policy={"max_attempts": 1},
        concurrency=5,
        code=CodeIdentity(commit=commit, dirty=False, package_version="0.1.0"),
        environment="test",
        requested_case_ids=("text-001",),
    )


def _summary_and_results(golden_suite: Path):
    suite = load_suite(golden_suite)
    case = suite.by_id("text-001")
    results = [
        CaseResult(
            run_id="run-1",
            case_id=case.case_id,
            primary_profile=case.primary_profile,
            sequence=0,
            state=CaseState.PASS,
            latency_ms=120,
            attempts=1,
        )
    ]
    return aggregate("run-1", [case], results), results


def test_escape_neutralizes_markdown_and_html() -> None:
    assert escape("a|b<c>&d`e\nf") == "a\\|b&lt;c&gt;&amp;d\\`e f"


def test_report_contains_required_sections(golden_suite: Path) -> None:
    summary, results = _summary_and_results(golden_suite)
    report = render_report(_manifest(), summary, results)
    assert "# Evaluation run run-1" in report
    assert "## Provenance" in report
    assert "## Summary" in report
    assert "## Profiles" in report
    assert "## Cases" in report
    assert "text-001" in report


def test_report_escapes_untrusted_metadata(golden_suite: Path) -> None:
    summary, results = _summary_and_results(golden_suite)
    report = render_report(
        _manifest(dataset_name="golden|v1<script>", commit="ab&c"),
        summary,
        results,
    )
    assert "<script>" not in report
    assert "golden\\|v1&lt;script&gt;" in report
    assert "ab&amp;c" in report


def test_json_payload_is_a_projection(golden_suite: Path) -> None:
    summary, _results = _summary_and_results(golden_suite)
    payload = summary_payload(_manifest(), summary)
    assert payload["run_id"] == "run-1"
    assert payload["dataset"]["name"] == "golden-v1"
    assert payload["summary"]["completed"] == 1
