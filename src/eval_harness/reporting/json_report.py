"""JSON report projection built only from stored domain results."""

from __future__ import annotations

from ..domain.runs import RunManifest, Summary

__all__ = ["summary_payload"]


def summary_payload(manifest: RunManifest, summary: Summary) -> dict[str, object]:
    return {
        "run_id": summary.run_id,
        "status": str(manifest.status),
        "dataset": {
            "name": manifest.dataset.name,
            "suite_version": manifest.dataset.suite_version,
            "content_hash": manifest.dataset.content_hash,
        },
        "target": manifest.target,
        "code": manifest.code.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
    }
