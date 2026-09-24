"""Unit tests for canonical hashing."""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.datasets.hashing import canonical_json, hash_bytes, suite_content_hash


def test_canonical_json_sorts_keys_and_strips_space() -> None:
    assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert canonical_json([2, 1]) == b"[2,1]"


def test_hash_bytes_known_vector() -> None:
    assert hash_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_suite_hash_is_stable(suite_copy: Path) -> None:
    assert suite_content_hash(suite_copy) == suite_content_hash(suite_copy)


def test_suite_hash_changes_when_content_changes(suite_copy: Path) -> None:
    before = suite_content_hash(suite_copy)
    cases = suite_copy / "cases.jsonl"
    cases.write_text(cases.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert suite_content_hash(suite_copy) != before


def test_manifest_content_hash_field_is_excluded(suite_copy: Path) -> None:
    before = suite_content_hash(suite_copy)
    manifest_path = suite_copy / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_hash"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert suite_content_hash(suite_copy) == before
