"""Local object-store backend and an artifact store over it.

Objects are immutable and content-hashed; a run bundle is uploaded object by
object with the ``COMPLETE`` marker written last, matching the filesystem
store's manifest-last contract. The production object store (S3/GCS) is a
Phase-08 deployment selection; this local backend is the default and the
contract test target.
"""

from __future__ import annotations

from pathlib import Path

from ...datasets.hashing import sha256_hex
from ...domain.baselines import BaselineRecord
from ...domain.runs import BundleIndex, RunManifest
from ...domain.waivers import Waiver
from ...errors import InfrastructureError
from .filesystem import FilesystemArtifactStore, RunWriter

__all__ = ["LocalObjectStore", "ObjectStoreArtifactStore"]


class LocalObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = Path(key)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise InfrastructureError("unsafe object key", details={"key": key})
        return self.objects / candidate

    def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        if path.exists():
            if path.read_bytes() != data:
                raise InfrastructureError("immutable object conflict", details={"key": key})
            return sha256_hex(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return sha256_hex(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise InfrastructureError("object not found", details={"key": key})
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        directory = base if base.is_dir() else base.parent
        results: list[str] = []
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            results.append(path.relative_to(self.objects).as_posix())
        return [key for key in results if key.startswith(prefix)]

    def delete(self, key: str) -> None:
        path = self._path(key)
        path.unlink(missing_ok=True)


class _UploadingWriter:
    def __init__(self, writer: RunWriter, store: LocalObjectStore, prefix: str) -> None:
        self._writer = writer
        self._store = store
        self._prefix = prefix

    @property
    def staging(self) -> Path:
        return self._writer.staging

    def write_json(self, name, payload) -> None:  # type: ignore[no-untyped-def]
        self._writer.write_json(name, payload)

    def write_jsonl(self, name, rows) -> None:  # type: ignore[no-untyped-def]
        self._writer.write_jsonl(name, rows)

    def write_text(self, name: str, text: str) -> None:
        self._writer.write_text(name, text)

    def finalize(self, final_dir: Path) -> BundleIndex:
        index = self._writer.finalize(final_dir)
        for name in index.files:
            self._store.put(f"{self._prefix}/{name}", (final_dir / name).read_bytes())
        self._store.put(f"{self._prefix}/COMPLETE", (final_dir / "COMPLETE").read_bytes())
        return index

    def abandon(self) -> None:
        self._writer.abandon()


class ObjectStoreArtifactStore:
    def __init__(self, store: LocalObjectStore, cache_root: Path) -> None:
        self._store = store
        self._fs = FilesystemArtifactStore(cache_root)

    def begin(self, run_id: str) -> _UploadingWriter:
        writer = self._fs.begin(run_id)
        return _UploadingWriter(writer, self._store, f"runs/{run_id}")

    def run_dir(self, run_id: str) -> Path:
        return self._fs.run_dir(run_id)

    def location(self, run_id: str) -> str:
        return f"object://runs/{run_id}"

    def _materialize(self, run_id: str) -> None:
        prefix = f"runs/{run_id}"
        target_dir = self._fs.run_dir(run_id)
        for key in self._store.list(prefix):
            name = key[len(prefix) + 1 :]
            target = target_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self._store.get(key))

    def read_bundle(self, run_id: str) -> dict[str, object]:
        self._materialize(run_id)
        return self._fs.read_bundle(run_id)

    def read_manifest(self, run_id: str) -> RunManifest:
        self._materialize(run_id)
        return self._fs.read_manifest(run_id)

    def baseline_exists(self, suite_name: str, channel: str) -> bool:
        return self._store.exists(f"baselines/{suite_name}/{channel}.json")

    def read_baseline(self, suite_name: str, channel: str) -> BaselineRecord:
        key = f"baselines/{suite_name}/{channel}.json"
        if not self._store.exists(key):
            raise InfrastructureError(
                "baseline channel does not exist",
                details={"suite": suite_name, "channel": channel},
            )
        return BaselineRecord.model_validate_json(self._store.get(key))

    def write_baseline(self, record: BaselineRecord) -> None:
        import json

        self._store.put(
            f"baselines/{record.suite_name}/{record.channel}.json",
            json.dumps(record.model_dump(mode="json"), sort_keys=True).encode("utf-8"),
        )

    def read_waiver(self, waiver_id: str) -> Waiver:
        key = f"waivers/{waiver_id}.json"
        if not self._store.exists(key):
            raise InfrastructureError("waiver does not exist", details={"waiver_id": waiver_id})
        return Waiver.model_validate_json(self._store.get(key))

    def write_waiver(self, waiver: Waiver) -> None:
        import json

        self._store.put(
            f"waivers/{waiver.waiver_id}.json",
            json.dumps(waiver.model_dump(mode="json"), sort_keys=True).encode("utf-8"),
        )
