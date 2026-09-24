"""Safe, streaming golden-suite loader.

All input is untrusted: paths are resolved beneath an approved root, files are
size-limited, records are strictly parsed, and a tampered checksum or hash
fails before any evaluation can run.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from ..domain.cases import EvalCase, Profile, parse_case
from ..errors import DatasetError
from .hashing import canonical_json, hash_file, sha256_hex, suite_content_hash
from .models import (
    Checksums,
    DatasetIdentity,
    DatasetLimits,
    LoadedSuite,
    Manifest,
)

__all__ = ["inspect_suite", "load_suite", "profile_distribution"]


def _read_bytes(path: Path, max_bytes: int, label: str) -> bytes:
    if not path.is_file():
        raise DatasetError(f"{label} is missing", details={"path": path.name})
    size = path.stat().st_size
    if size > max_bytes:
        raise DatasetError(
            f"{label} exceeds size limit",
            details={"path": path.name, "size": size, "limit": max_bytes},
        )
    return path.read_bytes()


def _resolve_suite_root(raw: Path, limits: DatasetLimits) -> Path:
    root = Path(raw)
    if not root.exists():
        raise DatasetError("suite root does not exist", details={"path": str(root)})
    if not root.is_dir():
        raise DatasetError("suite root is not a directory", details={"path": str(root)})
    resolved = root.resolve()
    if limits.allowed_root is not None:
        approved = limits.allowed_root.resolve()
        if not resolved.is_relative_to(approved):
            raise DatasetError(
                "suite root escapes the approved root",
                details={"path": str(resolved), "approved_root": str(approved)},
            )
    return resolved


def _json_depth(value: object) -> int:
    if isinstance(value, dict):
        return 1 + max((_json_depth(v) for v in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_json_depth(v) for v in value), default=0)
    return 0


def _load_manifest(root: Path, limits: DatasetLimits, errors: list[str]) -> Manifest | None:
    try:
        raw = _read_bytes(root / "manifest.json", limits.max_manifest_bytes, "manifest.json")
    except DatasetError as error:
        errors.append(error.message)
        return None
    try:
        return Manifest.model_validate_json(raw)
    except ValidationError as error:
        errors.append(f"manifest.json is invalid: {error.error_count()} error(s)")
        return None


def _load_checksums(root: Path, limits: DatasetLimits, errors: list[str]) -> Checksums | None:
    try:
        raw = _read_bytes(root / "checksums.json", limits.max_manifest_bytes, "checksums.json")
    except DatasetError as error:
        errors.append(error.message)
        return None
    try:
        return Checksums.model_validate_json(raw)
    except ValidationError:
        errors.append("checksums.json is invalid")
        return None


def _verify_checksums(root: Path, checksums: Checksums, errors: list[str]) -> None:
    actual = {
        path.relative_to(root).as_posix(): path
        for path in sorted(p for p in root.rglob("*") if p.is_file())
        if path.name != "checksums.json"
    }
    for relative, expected in checksums.files.items():
        path = actual.get(relative)
        if path is None:
            errors.append(f"checksums.json lists a missing file: {relative}")
            continue
        if hash_file(path) != expected:
            errors.append(f"checksum mismatch: {relative}")
    for relative in actual:
        if relative not in checksums.files:
            errors.append(f"file not covered by checksums.json: {relative}")


def _load_cases(root: Path, limits: DatasetLimits, errors: list[str]) -> list[EvalCase]:
    path = root / "cases.jsonl"
    try:
        _read_bytes(path, limits.max_fixture_bytes, "cases.jsonl")
    except DatasetError as error:
        errors.append(error.message)
        return []
    cases: list[EvalCase] = []
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip(b"\r\n")
            if not line.strip():
                errors.append(f"cases.jsonl line {line_number}: blank line")
                continue
            if len(line) > limits.max_case_bytes:
                errors.append(f"cases.jsonl line {line_number}: exceeds case size limit")
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                errors.append(f"cases.jsonl line {line_number}: malformed JSON")
                continue
            if _json_depth(payload) > limits.max_nesting:
                errors.append(f"cases.jsonl line {line_number}: exceeds nesting limit")
                continue
            try:
                cases.append(parse_case(payload))
            except ValidationError:
                errors.append(f"cases.jsonl line {line_number}: invalid case schema")
    return cases


def _verify_fixtures(
    root: Path, cases: list[EvalCase], limits: DatasetLimits, errors: list[str]
) -> None:
    for case in cases:
        for attachment in case.input.attachments:
            candidate = Path(attachment)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"{case.case_id}: fixture path is not relative: {attachment}")
                continue
            resolved = (root / candidate).resolve()
            if not resolved.is_relative_to(root):
                errors.append(f"{case.case_id}: fixture escapes suite root: {attachment}")
                continue
            if not resolved.is_file():
                errors.append(f"{case.case_id}: missing fixture: {attachment}")
                continue
            if resolved.stat().st_size > limits.max_fixture_bytes:
                errors.append(f"{case.case_id}: fixture too large: {attachment}")


def _check_suite_invariants(
    manifest: Manifest | None,
    cases: list[EvalCase],
    limits: DatasetLimits,
    errors: list[str],
) -> None:
    if len(cases) > limits.max_cases:
        errors.append(f"case count exceeds limit: {len(cases)} > {limits.max_cases}")
    ids = [case.case_id for case in cases]
    duplicates = sorted(case_id for case_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate case_id(s): {duplicates}")
    fingerprints = Counter(
        sha256_hex(canonical_json(case.model_dump(mode="json"))) for case in cases
    )
    if any(count > 1 for count in fingerprints.values()):
        errors.append("duplicate case content detected")
    if manifest is None:
        return
    if manifest.case_count != len(cases):
        errors.append(f"case_count mismatch: manifest={manifest.case_count} actual={len(cases)}")
    actual_profiles = Counter(case.primary_profile.value for case in cases)
    for profile, expected in manifest.profile_counts.items():
        if actual_profiles.get(profile, 0) != expected:
            errors.append(
                f"profile count mismatch for {profile}: "
                f"manifest={expected} actual={actual_profiles.get(profile, 0)}"
            )
    unknown_profiles = sorted(set(actual_profiles) - set(manifest.profile_counts))
    if unknown_profiles:
        errors.append(f"cases use profiles absent from the manifest: {unknown_profiles}")


def inspect_suite(
    path: Path, limits: DatasetLimits | None = None
) -> tuple[DatasetIdentity | None, tuple[EvalCase, ...], tuple[str, ...]]:
    """Inspect a suite without raising; return identity, cases, and errors."""

    effective = limits if limits is not None else DatasetLimits()
    errors: list[str] = []
    try:
        root = _resolve_suite_root(path, effective)
    except DatasetError as error:
        return None, (), (error.message,)

    manifest = _load_manifest(root, effective, errors)
    checksums = _load_checksums(root, effective, errors)
    if checksums is not None:
        _verify_checksums(root, checksums, errors)
        if manifest is not None and checksums.algorithm != manifest.content_hash_algorithm:
            errors.append("checksum algorithm does not match manifest")

    computed_hash = suite_content_hash(root)
    if manifest is not None and manifest.content_hash != computed_hash:
        errors.append(
            "suite content hash mismatch: "
            f"manifest={manifest.content_hash} computed={computed_hash}"
        )

    cases = _load_cases(root, effective, errors)
    _check_suite_invariants(manifest, cases, effective, errors)
    _verify_fixtures(root, cases, effective, errors)

    identity: DatasetIdentity | None = None
    if manifest is not None:
        identity = DatasetIdentity(
            name=manifest.name,
            suite_version=manifest.suite_version,
            schema_version=manifest.schema_version,
            content_hash=computed_hash,
            case_ids=tuple(sorted(case.case_id for case in cases)),
        )
    return identity, tuple(cases), tuple(errors)


def load_suite(path: Path, limits: DatasetLimits | None = None) -> LoadedSuite:
    """Load and validate a suite, raising :class:`DatasetError` on any error."""

    effective = limits if limits is not None else DatasetLimits()
    root = _resolve_suite_root(path, effective)
    identity, cases, errors = inspect_suite(root, effective)
    if errors:
        raise DatasetError(errors[0], details={"errors": list(errors)})
    if identity is None:
        raise DatasetError("suite manifest is missing")
    ordered = tuple(sorted(cases, key=lambda case: case.case_id))
    if len(ordered) != len(cases):
        raise DatasetError("case ordering produced duplicates")
    return LoadedSuite(root=root, identity=identity, cases=ordered)


def profile_distribution(cases: tuple[EvalCase, ...]) -> dict[Profile, int]:
    counts: dict[Profile, int] = {}
    for case in cases:
        counts[case.primary_profile] = counts.get(case.primary_profile, 0) + 1
    return counts
