"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_harness_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ambient harness variables so tests never depend on the shell."""

    for key in list(os.environ):
        if key.startswith("EVAL_HARNESS_"):
            monkeypatch.delenv(key, raising=False)
