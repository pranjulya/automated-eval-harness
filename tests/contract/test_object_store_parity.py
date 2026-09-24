"""Filesystem and object-store implement the same bundle contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.adapters.artifacts.object_store import (
    LocalObjectStore,
    ObjectStoreArtifactStore,
)
from eval_harness.errors import InfrastructureError


def _write_bundle(store, run_id: str) -> None:
    writer = store.begin(run_id)
    writer.write_json("manifest.json", {"status": "completed"})
    writer.write_jsonl("cases.jsonl", [{"case_id": "text-001", "state": "PASS"}])
    writer.write_text("report.md", "# report\n")
    writer.write_json("summary.json", {"completed": 1, "pass_rate": 1.0})
    writer.finalize(store.run_dir(run_id))


def test_filesystem_and_object_store_parity(tmp_path: Path) -> None:
    filesystem = FilesystemArtifactStore(tmp_path / "fs")
    object_store = ObjectStoreArtifactStore(LocalObjectStore(tmp_path / "obj"), tmp_path / "cache")
    _write_bundle(filesystem, "r1")
    _write_bundle(object_store, "r2")

    filesystem.read_bundle("r1")
    object_store.read_bundle("r2")

    assert (filesystem.run_dir("r1") / "summary.json").read_bytes() == (
        object_store.run_dir("r2") / "summary.json"
    ).read_bytes()
    assert (filesystem.run_dir("r1") / "manifest.json").read_bytes() == (
        object_store.run_dir("r2") / "manifest.json"
    ).read_bytes()
    assert object_store.location("r2") == "object://runs/r2"


def test_object_store_rejects_unsafe_keys(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "obj")
    with pytest.raises(InfrastructureError):
        store.put("../escape", b"x")
    with pytest.raises(InfrastructureError):
        store.put("/absolute", b"x")


def test_object_store_is_immutable(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "obj")
    store.put("k", b"one")
    store.put("k", b"one")  # identical write is allowed
    with pytest.raises(InfrastructureError, match="immutable object conflict"):
        store.put("k", b"two")


def test_object_store_detects_missing_object(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "obj")
    with pytest.raises(InfrastructureError, match="not found"):
        store.get("absent")


def test_object_store_reads_reject_tampering(tmp_path: Path) -> None:
    object_backend = LocalObjectStore(tmp_path / "obj")
    artifact_store = ObjectStoreArtifactStore(object_backend, tmp_path / "cache")
    _write_bundle(artifact_store, "r1")
    # Tamper with a stored object; integrity verification must fail on read.
    object_backend._path("runs/r1/summary.json").write_bytes(b'{"completed": 999}')
    with pytest.raises(InfrastructureError):
        artifact_store.read_bundle("r1")
