"""Filesystem artifact store with atomic staging/finalize publication."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...datasets.hashing import canonical_json, hash_file, sha256_hex
from ...domain.runs import RUN_SCHEMA_VERSION, BundleIndex, RunManifest
from ...errors import InfrastructureError

__all__ = ["FilesystemArtifactStore", "RunWriter"]

RUN_FILES = (
    "manifest.json",
    "inputs.jsonl",
    "attempts.jsonl",
    "cases.jsonl",
    "outcomes.jsonl",
    "summary.json",
    "report.md",
)


class RunWriter:
    """Write into a staging directory; finalize atomically."""

    def __init__(self, staging: Path, run_id: str) -> None:
        self._staging = staging
        self._run_id = run_id
        self._staging.mkdir(parents=True, exist_ok=False)

    @property
    def staging(self) -> Path:
        return self._staging

    def write_json(self, name: str, payload: Any) -> None:
        _write_text(self._staging / name, canonical_json(payload).decode("utf-8"))

    def write_jsonl(self, name: str, rows: list[Any]) -> None:
        text = "".join(canonical_json(row).decode("utf-8") + "\n" for row in rows)
        _write_text(self._staging / name, text)

    def write_text(self, name: str, text: str) -> None:
        _write_text(self._staging / name, text)

    def finalize(self, final_dir: Path) -> BundleIndex:
        files = {
            path.name: hash_file(path) for path in sorted(self._staging.iterdir()) if path.is_file()
        }
        index_hash = sha256_hex(canonical_json(files))
        index = BundleIndex(
            schema_version=RUN_SCHEMA_VERSION,
            run_id=self._run_id,
            files=files,
            index_hash=index_hash,
            created=datetime.now(UTC).isoformat(),
        )
        _write_text(
            self._staging / "COMPLETE",
            canonical_json(index.model_dump(mode="json")).decode("utf-8"),
        )
        if final_dir.exists():
            raise InfrastructureError("run id already exists", details={"run_id": self._run_id})
        try:
            os.rename(self._staging, final_dir)
        except OSError as error:
            raise InfrastructureError(
                "failed to publish run bundle",
                details={"reason": error.strerror or error.__class__.__name__},
            ) from error
        return index

    def abandon(self) -> None:
        shutil.rmtree(self._staging, ignore_errors=True)


def _write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


class FilesystemArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.runs = self.root / "runs"
        self.runs.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        return self.runs / run_id

    def begin(self, run_id: str) -> RunWriter:
        nonce = sha256_hex(os.urandom(16))[:12]
        staging = self.runs / f".{run_id}.staging-{nonce}"
        return RunWriter(staging, run_id)

    def read_bundle(self, run_id: str) -> dict[str, Any]:
        bundle = self.run_dir(run_id)
        marker = bundle / "COMPLETE"
        if not marker.is_file():
            raise InfrastructureError(
                "run bundle is incomplete or missing", details={"run_id": run_id}
            )
        index = BundleIndex.model_validate_json(marker.read_text(encoding="utf-8"))
        for name, expected in index.files.items():
            path = bundle / name
            if not path.is_file() or hash_file(path) != expected:
                raise InfrastructureError(
                    "run bundle failed integrity check", details={"file": name}
                )
        return {
            "index": index,
            "manifest": (bundle / "manifest.json").read_text(encoding="utf-8"),
            "bundle": bundle,
        }

    def list_runs(self) -> list[str]:
        return sorted(
            path.name
            for path in self.runs.iterdir()
            if path.is_dir() and not path.name.startswith(".") and (path / "COMPLETE").is_file()
        )

    def read_manifest(self, run_id: str) -> RunManifest:
        bundle = self.run_dir(run_id)
        if not (bundle / "COMPLETE").is_file():
            raise InfrastructureError(
                "run bundle is incomplete or missing", details={"run_id": run_id}
            )
        return RunManifest.model_validate_json(
            (bundle / "manifest.json").read_text(encoding="utf-8")
        )
