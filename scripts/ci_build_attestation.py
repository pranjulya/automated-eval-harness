#!/usr/bin/env python3
"""Build a gate attestation from the CI gate job's environment.

Reads: RUN_ID, DECISION, REASON_CODES, GITHUB_SHA. Writes attestation.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from eval_harness.datasets.hashing import hash_file
from eval_harness.domain.attestations import build_attestation
from eval_harness.domain.gates import GateDecision


def main() -> None:
    run_id = os.environ["RUN_ID"]
    decision = GateDecision(os.environ.get("DECISION", "REVIEW_REQUIRED"))
    reason_codes = tuple(code for code in os.environ.get("REASON_CODES", "").split(",") if code)
    artifact_root = Path(os.environ.get("EVAL_HARNESS_ARTIFACT_ROOT", "artifacts"))
    bundle = artifact_root / "runs" / run_id
    baseline_path = artifact_root / "baselines" / "golden-v1" / "stable.json"
    baseline_hash = (
        json.loads(baseline_path.read_text(encoding="utf-8"))["record_hash"]
        if baseline_path.is_file()
        else "absent"
    )
    attestation = build_attestation(
        commit=os.environ.get("GITHUB_SHA", "unknown"),
        run_id=run_id,
        run_manifest_hash=hash_file(bundle / "manifest.json"),
        baseline_hash=baseline_hash,
        workflow=".github/workflows/eval-release.yml",
        decision=decision,
        reason_codes=reason_codes,
    )
    Path("attestation.json").write_text(attestation.model_dump_json(indent=2), encoding="utf-8")
    print(attestation.attestation_hash)


if __name__ == "__main__":
    main()
