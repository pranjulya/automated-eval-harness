#!/usr/bin/env python3
"""Generate deterministic fake-target responses for every golden-v1 case.

Run from the repository root:
    python3.12 scripts/generate_fake_target_v1.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evaluation" / "datasets" / "golden-v1" / "cases.jsonl"
OUTPUT = ROOT / "evaluation" / "fixtures" / "fake-target-v1.json"

ORDER_DOCUMENT = {
    "order": {
        "id": "A1",
        "total": 10.0,
        "status": "paid",
        "quantity": 2,
        "items": [{}, {}, {}],
    }
}


def text_response(case: dict) -> dict:
    deterministic = case["expectation"]["deterministic"]
    if deterministic.get("trusted_regex"):
        return {"status": "ok", "text": "order-4821"}
    required = deterministic.get("required_values") or []
    return {"status": "ok", "text": " ".join(required) or "ok"}


def safety_response(case: dict) -> dict:
    outcome = case["expectation"]["deterministic"]["required_outcome"]
    if outcome == "refused":
        return {"status": "ok", "text": "I cannot help with that request."}
    if outcome == "insufficient_evidence":
        return {"status": "ok", "text": ""}
    return {"status": "ok", "text": "Support hours are 09:00-18:00 UTC, Monday to Friday."}


def structured_response(case: dict) -> dict:
    del case
    return {"status": "ok", "structured": ORDER_DOCUMENT, "text": json.dumps(ORDER_DOCUMENT)}


def rag_response(case: dict) -> dict:
    deterministic = case["expectation"]["deterministic"]
    if not deterministic["answerable"]:
        return {"status": "ok", "text": ""}
    labels = deterministic["relevant_evidence"]
    evidence = [
        {"document_id": label["document_id"], "evidence_id": label["evidence_id"], "rank": rank}
        for rank, label in enumerate(labels, start=1)
    ]
    cited = deterministic.get("required_citation_ids") or [label["evidence_id"] for label in labels]
    citations = [{"claim_id": "c1", "evidence_ids": cited}]
    return {
        "status": "ok",
        "text": "Answer grounded in the cited evidence.",
        "evidence": evidence,
        "citations": citations,
    }


def tool_response(case: dict) -> dict:
    deterministic = case["expectation"]["deterministic"]
    calls = [
        {"name": call["name"], "arguments": call.get("arguments", {})}
        for call in deterministic.get("expected_calls", [])
    ]
    return {"status": "ok", "text": "Done.", "tool_calls": calls}


def build() -> dict[str, dict]:
    responses: dict[str, dict] = {}
    for line in SUITE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        profile = case["primary_profile"]
        if profile == "text_semantic":
            responses[case["case_id"]] = text_response(case)
        elif profile == "safety_abstention":
            responses[case["case_id"]] = safety_response(case)
        elif profile == "structured_output":
            responses[case["case_id"]] = structured_response(case)
        elif profile == "rag":
            responses[case["case_id"]] = rag_response(case)
        elif profile == "tool_use":
            responses[case["case_id"]] = tool_response(case)
        else:  # pragma: no cover
            raise ValueError(f"unknown profile: {profile}")
    return dict(sorted(responses.items()))


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    OUTPUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(data)} fake responses to {OUTPUT.relative_to(ROOT)}")
