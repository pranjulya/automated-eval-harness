"""Shared test fixtures."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
VALIDATION_CONFIG = REPO_ROOT / "evaluation" / "configs" / "validation.json"


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
