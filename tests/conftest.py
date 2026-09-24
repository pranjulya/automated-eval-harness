"""Shared test fixtures."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from eval_harness.adapters.targets import FakeTargetAdapter, load_fake_responses
from eval_harness.adapters.targets.base import TargetConfig
from eval_harness.application.run import RunConfig, RunService
from eval_harness.domain.runs import CodeIdentity
from eval_harness.evaluators import build_registry, load_schema_resolver

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
VALIDATION_CONFIG = REPO_ROOT / "evaluation" / "configs" / "validation.json"
FAKE_RESPONSES = REPO_ROOT / "evaluation" / "fixtures" / "fake-target-v1.json"


@pytest.fixture(autouse=True)
def _isolate_harness_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ambient harness variables so tests never depend on the shell."""

    for key in list(os.environ):
        if key.startswith("EVAL_HARNESS_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def golden_suite() -> Path:
    return GOLDEN_V1


@pytest.fixture
def suite_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "golden-v1"
    shutil.copytree(GOLDEN_V1, destination)
    return destination


@pytest.fixture
def validation_config() -> Path:
    return VALIDATION_CONFIG


def schema_resolver(repo_root: Path) -> Callable[[str], dict[str, Any] | None]:
    return load_schema_resolver(repo_root)


@pytest.fixture
def run_factory(tmp_path: Path) -> Callable[..., tuple[RunService, RunConfig]]:
    def make(
        *,
        adapter: Any | None = None,
        artifact_root: Path | None = None,
        concurrency: int = 5,
    ) -> tuple[RunService, RunConfig]:
        active_adapter = adapter or FakeTargetAdapter(load_fake_responses(FAKE_RESPONSES))
        registry = build_registry(schema_resolver(REPO_ROOT))
        service = RunService(
            adapter=active_adapter,
            registry=registry,
            code=CodeIdentity(commit="test", dirty=False, package_version="0.1.0"),
        )
        config = RunConfig(
            target=TargetConfig(adapter="fake", model="fake-v1", idempotent=True),
            concurrency=concurrency,
            artifact_root=str(artifact_root or (tmp_path / "artifacts")),
            fake_responses=str(FAKE_RESPONSES),
        )
        return service, config

    return make
