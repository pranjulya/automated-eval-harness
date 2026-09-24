"""Dataset value objects shared by the loader and validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..domain.cases import EvalCase, Profile

__all__ = [
    "Checksums",
    "DatasetIdentity",
    "DatasetLimits",
    "LoadedSuite",
    "Manifest",
    "ValidationConfig",
    "ValidationReport",
]


class Manifest(BaseModel):
    """Strict `manifest.json` contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    suite_version: str
    schema_version: str
    case_count: int = Field(gt=0)
    profile_counts: dict[str, int]
    fixture_roots: tuple[str, ...] = ("fixtures",)
    owners: tuple[str, ...] = Field(min_length=1)
    created: str
    content_hash_algorithm: str
    content_hash: str
    tags: tuple[str, ...]
    intended_targets: tuple[str, ...]
    license: str
    privacy_classification: str


class Checksums(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    algorithm: str
    files: dict[str, str]


@dataclass(frozen=True, slots=True)
class DatasetLimits:
    """Resource and containment limits applied to untrusted dataset input."""

    max_cases: int = 200
    max_case_bytes: int = 65_536
    max_manifest_bytes: int = 65_536
    max_fixture_bytes: int = 1_048_576
    max_nesting: int = 32
    allowed_root: Path | None = None


@dataclass(frozen=True, slots=True)
class DatasetIdentity:
    name: str
    suite_version: str
    schema_version: str
    content_hash: str
    case_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoadedSuite:
    root: Path
    identity: DatasetIdentity
    cases: tuple[EvalCase, ...]

    def by_id(self, case_id: str) -> EvalCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)

    def profile_counts(self) -> dict[Profile, int]:
        counts: dict[Profile, int] = {}
        for case in self.cases:
            counts[case.primary_profile] = counts.get(case.primary_profile, 0) + 1
        return counts


@dataclass(frozen=True, slots=True)
class ValidationReport:
    ok: bool
    root: Path
    identity: DatasetIdentity | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ok": self.ok,
            "suite": str(self.root),
            "errors": list(self.errors),
        }
        if self.identity is not None:
            payload["identity"] = {
                "name": self.identity.name,
                "suite_version": self.identity.suite_version,
                "schema_version": self.identity.schema_version,
                "content_hash": self.identity.content_hash,
                "case_count": len(self.identity.case_ids),
            }
        return payload


class ValidationConfig(BaseModel):
    """Strict `evaluation/configs/validation.json` contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_cases: int = Field(default=200, gt=0)
    max_case_bytes: int = Field(default=65_536, gt=0)
    max_manifest_bytes: int = Field(default=65_536, gt=0)
    max_fixture_bytes: int = Field(default=1_048_576, gt=0)
    max_nesting: int = Field(default=32, gt=0)
    allowed_root: Path | None = None

    def to_limits(self, base_dir: Path) -> DatasetLimits:
        allowed_root = self.allowed_root
        if allowed_root is not None and not allowed_root.is_absolute():
            allowed_root = base_dir / allowed_root
        return DatasetLimits(
            max_cases=self.max_cases,
            max_case_bytes=self.max_case_bytes,
            max_manifest_bytes=self.max_manifest_bytes,
            max_fixture_bytes=self.max_fixture_bytes,
            max_nesting=self.max_nesting,
            allowed_root=allowed_root,
        )
