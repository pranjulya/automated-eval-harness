"""The shipped regressed demo target must BLOCK against a clean baseline (local quickstart)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_harness.cli import main
from eval_harness.errors import ExitCode

REPO_ROOT = Path(__file__).resolve().parents[2]
SUITE = "evaluation/datasets/golden-v1"


def test_regressed_fake_target_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("EVAL_HARNESS_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    approval = tmp_path / "approval.json"
    approval.write_text(
        json.dumps({"actor": "me", "approval_evidence": ["local-review"], "reason": "baseline"})
    )

    base = ["run", "--suite", SUITE, "--config", "evaluation/configs/fake.json"]
    assert main([*base, "--run-id", "clean"]) == ExitCode.SUCCESS
    promote = ["promote-baseline", "--run", "clean", "--suite", "golden-v1", "--channel", "stable"]
    assert main([*promote, "--reason", "baseline", "--approval-file", str(approval)]) == 0

    regressed = ["run", "--suite", SUITE, "--config", "evaluation/configs/fake-regressed.json"]
    main([*regressed, "--run-id", "regressed"])
    capsys.readouterr()

    compare = [
        "compare",
        "--candidate",
        "regressed",
        "--baseline",
        "stable",
        "--suite",
        "golden-v1",
    ]
    assert main(compare) == ExitCode.BLOCK
    out = capsys.readouterr().out
    assert "decision=BLOCK" in out
    assert "HARD_INVARIANT_FORBIDDEN_TOOL" in out
    assert "HARD_INVARIANT_SCHEMA" in out
