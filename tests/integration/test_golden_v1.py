"""Integration tests for the reviewed golden-v1 suite."""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.cli import main
from eval_harness.datasets import load_suite
from eval_harness.domain.cases import Profile

EXPECTED_COUNTS = {
    Profile.TEXT_SEMANTIC: 12,
    Profile.SAFETY_ABSTENTION: 6,
    Profile.STRUCTURED_OUTPUT: 10,
    Profile.RAG: 12,
    Profile.TOOL_USE: 10,
}

HARD_INVARIANT_CASES = {"struct-004", "tool-008", "rag-008", "rag-011", "safe-005"}


def test_exactly_50_unique_ordered_ids(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    ids = [case.case_id for case in suite.cases]
    assert len(ids) == 50
    assert ids == sorted(ids)
    assert len(set(ids)) == 50


def test_locked_profile_distribution(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    assert suite.profile_counts() == EXPECTED_COUNTS


def test_identity_hash_matches_manifest(golden_suite: Path) -> None:
    manifest = json.loads((golden_suite / "manifest.json").read_text(encoding="utf-8"))
    suite = load_suite(golden_suite)
    assert suite.identity.content_hash == manifest["content_hash"]
    assert suite.identity.suite_version == "1.0.1"
    assert suite.identity.schema_version == "eval.case.v1"


def test_hard_invariant_cases_present(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    ids = {case.case_id for case in suite.cases}
    assert ids >= HARD_INVARIANT_CASES


def test_every_rag_case_is_answerability_consistent(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    for case in suite.cases:
        if case.primary_profile is not Profile.RAG:
            continue
        deterministic = case.expectation.deterministic  # type: ignore[union-attr]
        assert deterministic.answerable == bool(deterministic.relevant_evidence)


def test_cli_validate_reports_hash(golden_suite: Path, validation_config: Path, capsys) -> None:
    assert main(["validate", "--suite", str(golden_suite), "--config", str(validation_config)]) == 0
    out = capsys.readouterr().out
    assert "OK golden-v1 1.0.1" in out
    assert "cases=50" in out


def test_cli_validate_json_format(golden_suite: Path, validation_config: Path, capsys) -> None:
    assert (
        main(
            [
                "validate",
                "--suite",
                str(golden_suite),
                "--config",
                str(validation_config),
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["identity"]["case_count"] == 50


def test_cli_validate_tampered_suite_exits_four(suite_copy: Path, validation_config: Path) -> None:
    (suite_copy / "cases.jsonl").write_text("tampered\n", encoding="utf-8")
    assert main(["validate", "--suite", str(suite_copy), "--config", str(validation_config)]) == 4


def test_cli_invalid_validation_config_exits_four(
    tmp_path: Path, golden_suite: Path, capsys
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"unknown": 1}', encoding="utf-8")
    assert main(["validate", "--suite", str(golden_suite), "--config", str(bad)]) == 4
    assert json.loads(capsys.readouterr().err)["code"] == "CONFIG_INVALID"
