#!/usr/bin/env python3
"""Generate the four versioned judge rubrics.

Run from the repository root:
    python3.12 scripts/generate_rubrics.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBRICS = ROOT / "evaluation" / "rubrics"

ANCHORS = {
    1: "Not at all; wrong or irrelevant.",
    2: "Mostly missing or misleading.",
    3: "Partially correct; notable gaps or noise.",
    4: "Mostly correct; minor gaps.",
    5: "Fully correct for the stated dimension.",
}

NORMALIZED = {"1": 0.0, "2": 0.25, "3": 0.5, "4": 0.75, "5": 1.0}

RUBRIC_DEFS = {
    "relevance": "Judge only whether the candidate answer addresses the user's question. Ignore style, length, and formatting.",
    "faithfulness": "Judge only whether every factual claim in the candidate is supported by the provided evidence. Unsupported claims lower the score.",
    "completeness": "Judge only whether the candidate covers every required part of the reference answer. Extra correct detail does not raise the score.",
    "citation-support": "Judge only whether each cited evidence identity actually supports the claim it is attached to. Fabricated or mismatched citations lower the score.",
}


def build(rubric_id: str, dimension: str, instructions: str, version: str = "1.0.0") -> dict:
    return {
        "rubric_id": rubric_id,
        "version": version,
        "dimension": dimension,
        "anchors": [
            {"score": score, "description": text} for score, text in sorted(ANCHORS.items())
        ],
        "normalized_map": NORMALIZED,
        "pass_cut": 0.75,
        "prompt_hash": "sha256:" + hashlib.sha256(instructions.encode("utf-8")).hexdigest(),
        "instructions": instructions,
    }


if __name__ == "__main__":
    RUBRICS.mkdir(parents=True, exist_ok=True)
    for name, dimension in [
        ("relevance", "relevance"),
        ("faithfulness", "faithfulness"),
        ("completeness", "completeness"),
        ("citation-support", "citation_support"),
    ]:
        payload = build(f"{name}-v1", dimension, RUBRIC_DEFS[name])
        (RUBRICS / f"{name}-v1.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print("wrote 4 rubrics")
