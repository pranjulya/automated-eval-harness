"""Unit tests for suite validation and loader security/failure paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_harness.datasets import inspect_suite, load_suite, validate_suite
from eval_harness.datasets.models import DatasetLimits
from eval_harness.errors import DatasetError


def _errors(suite: Path, limits: DatasetLimits | None = None) -> list[str]:
    return list(validate_suite(suite, limits).errors)


def _first_case(suite: Path) -> dict[str, object]:
    first_line = (suite / "cases.jsonl").read_text(encoding="utf-8").splitlines()[0]
    return json.loads(first_line)


def _append_case(suite: Path, case: dict[str, object]) -> None:
    cases = suite / "cases.jsonl"
    with cases.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(case) + "\n")


def test_valid_suite_passes(suite_copy: Path) -> None:
    report = validate_suite(suite_copy)
    assert report.ok, report.errors
    assert report.identity is not None
    assert len(report.identity.case_ids) == 50


def test_missing_manifest(tmp_path: Path) -> None:
    assert "manifest.json is missing" in _errors(tmp_path)


def test_checksum_mismatch_is_detected(suite_copy: Path) -> None:
    (suite_copy / "cases.jsonl").write_text("tampered\n", encoding="utf-8")
    errors = _errors(suite_copy)
    assert any("checksum mismatch: cases.jsonl" in error for error in errors)


def test_uncovered_file_is_detected(suite_copy: Path) -> None:
    (suite_copy / "extra.txt").write_text("x", encoding="utf-8")
    errors = _errors(suite_copy)
    assert any("not covered by checksums.json" in error for error in errors)


def test_content_hash_mismatch_is_detected(suite_copy: Path) -> None:
    manifest_path = suite_copy / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_hash"] = "f" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = _errors(suite_copy)
    assert any("suite content hash mismatch" in error for error in errors)


def test_duplicate_case_id_is_detected(suite_copy: Path) -> None:
    _append_case(suite_copy, _first_case(suite_copy))
    errors = _errors(suite_copy)
    assert any("duplicate case_id" in error for error in errors)


def test_case_count_mismatch_is_detected(suite_copy: Path) -> None:
    manifest_path = suite_copy / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["case_count"] = 49
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = _errors(suite_copy)
    assert any("case_count mismatch" in error for error in errors)


def test_profile_count_mismatch_is_detected(suite_copy: Path) -> None:
    manifest_path = suite_copy / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profile_counts"]["rag"] = 11
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = _errors(suite_copy)
    assert any("profile count mismatch for rag" in error for error in errors)


def test_invalid_case_schema_is_detected(suite_copy: Path) -> None:
    cases = suite_copy / "cases.jsonl"
    with cases.open("a", encoding="utf-8") as handle:
        handle.write("{not valid json\n")
        handle.write(json.dumps({"case_id": "text-999"}) + "\n")
    errors = _errors(suite_copy)
    assert any("malformed JSON" in error for error in errors)
    assert any("invalid case schema" in error for error in errors)


def test_blank_line_is_detected(suite_copy: Path) -> None:
    cases = suite_copy / "cases.jsonl"
    with cases.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    errors = _errors(suite_copy)
    assert any("blank line" in error for error in errors)


def test_oversize_case_is_detected(suite_copy: Path) -> None:
    errors = _errors(suite_copy, DatasetLimits(max_case_bytes=16))
    assert any("exceeds case size limit" in error for error in errors)


def test_nesting_limit_is_detected(suite_copy: Path) -> None:
    errors = _errors(suite_copy, DatasetLimits(max_nesting=1))
    assert any("exceeds nesting limit" in error for error in errors)


def test_fixture_traversal_is_detected(suite_copy: Path) -> None:
    case = _first_case(suite_copy)
    case["case_id"] = "rag-099"
    case["input"]["attachments"] = ["../outside.txt"]  # type: ignore[index]
    _append_case(suite_copy, case)
    errors = _errors(suite_copy)
    assert any("not relative" in error for error in errors)


def test_missing_fixture_is_detected(suite_copy: Path) -> None:
    case = _first_case(suite_copy)
    case["case_id"] = "rag-098"
    case["input"]["attachments"] = ["fixtures/documents/missing.txt"]  # type: ignore[index]
    _append_case(suite_copy, case)
    errors = _errors(suite_copy)
    assert any("missing fixture" in error for error in errors)


def test_allowed_root_escape_is_rejected(suite_copy: Path, tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    errors = _errors(suite_copy, DatasetLimits(allowed_root=approved))
    assert errors == ["suite root escapes the approved root"]


def test_load_suite_raises_with_all_errors(suite_copy: Path) -> None:
    (suite_copy / "cases.jsonl").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(DatasetError) as excinfo:
        load_suite(suite_copy)
    assert excinfo.value.code == "DATASET_INVALID"
    assert len(excinfo.value.details["errors"]) >= 1  # type: ignore[arg-type]


def test_inspect_suite_never_raises(suite_copy: Path) -> None:
    (suite_copy / "manifest.json").unlink()
    _identity, _cases, errors = inspect_suite(suite_copy)
    assert errors
