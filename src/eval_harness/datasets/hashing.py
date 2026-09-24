"""Canonical hashing for datasets and artifacts.

The suite content hash is computed over a canonical sorted list of
``(relative_path, sha256)`` pairs, excluding ``checksums.json`` itself, so that
adding or changing any input changes the identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final

__all__ = [
    "canonical_json",
    "hash_bytes",
    "hash_file",
    "sha256_hex",
    "suite_content_hash",
]

_CHUNK: Final = 1 << 16


def canonical_json(value: object) -> bytes:
    """Serialize to canonical UTF-8 JSON: sorted keys, no insignificant space."""

    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_bytes(data: bytes) -> str:
    return sha256_hex(data)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def suite_content_hash(
    root: Path, *, exclude: frozenset[str] = frozenset({"checksums.json"})
) -> str:
    """Hash every file under ``root`` except the excluded relative paths.

    ``manifest.json`` is canonicalized with its own ``content_hash`` field
    removed, so the declared suite hash is not self-referential; every other
    file is hashed byte-for-byte.
    """

    pairs: list[list[str]] = []
    base = root.resolve()
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        relative = path.relative_to(base).as_posix()
        if relative in exclude:
            continue
        if relative == "manifest.json":
            data = json.loads(path.read_bytes())
            if isinstance(data, dict):
                data.pop("content_hash", None)
            digest = sha256_hex(canonical_json(data))
        else:
            digest = hash_file(path)
        pairs.append([relative, digest])
    pairs.sort(key=lambda item: item[0])
    return sha256_hex(canonical_json(pairs))
