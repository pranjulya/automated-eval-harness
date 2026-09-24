"""Markdown report projection (escapes untrusted text)."""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.runs import CaseResult, RunManifest, Summary

__all__ = ["escape", "render_report"]


def escape(value: str) -> str:
    """Escape Markdown/HTML-sensitive characters in untrusted text."""

    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("\n", " ")
    )


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def render_report(manifest: RunManifest, summary: Summary, results: Sequence[CaseResult]) -> str:
    lines: list[str] = []
    lines.append(f"# Evaluation run {escape(manifest.run_id)}")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(
        f"| Dataset | {escape(manifest.dataset.name)} {escape(manifest.dataset.suite_version)} |"
    )
    lines.append(f"| Suite hash | `{escape(manifest.dataset.content_hash)}` |")
    adapter_name = escape(str(manifest.target.get("adapter", "unknown")))
    model_name = escape(str(manifest.target.get("model", "unknown")))
    lines.append(f"| Target | {adapter_name} / {model_name} |")
    lines.append(f"| Commit | `{escape(manifest.code.commit)}` (dirty={manifest.code.dirty}) |")
    lines.append(f"| Status | {escape(str(manifest.status))} |")

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Expected | {summary.expected} |")
    lines.append(f"| Completed | {summary.completed} |")
    lines.append(f"| Pass rate | {_fmt(summary.pass_rate)} |")
    lines.append(f"| Invariant failures | {summary.invariant_failures} |")
    lines.append(f"| Semantic reviews | {summary.semantic_reviews} |")
    lines.append(f"| p95 latency (ms) | {_fmt(summary.p95_latency_ms)} |")
    lines.append(f"| Total cost (USD) | {_fmt(summary.total_cost_usd)} |")
    lines.append(f"| Comparable | {summary.comparable} |")

    lines.append("")
    lines.append("## Profiles")
    lines.append("")
    lines.append("| Profile | Expected | Completed | Passed | Pass rate |")
    lines.append("|---|---:|---:|---:|---:|")
    for profile in summary.profiles:
        lines.append(
            f"| {escape(profile.profile.value)} | {profile.expected} | {profile.completed} "
            f"| {profile.passed} | {_fmt(profile.pass_rate)} |"
        )

    lines.append("")
    lines.append("## Case states")
    lines.append("")
    lines.append("| State | Count |")
    lines.append("|---|---:|")
    for state, count in sorted(summary.state_counts.items()):
        lines.append(f"| {escape(state)} | {count} |")

    lines.append("")
    lines.append("## Cases")
    lines.append("")
    lines.append("| Case | Profile | State | First failing code |")
    lines.append("|---|---|---|---|")
    for result in results:
        failing = next((finding.code for finding in result.findings if finding.is_failure), "")
        lines.append(
            f"| {escape(result.case_id)} | {escape(result.primary_profile.value)} "
            f"| {escape(result.state.value)} | {escape(failing)} |"
        )
    lines.append("")
    return "\n".join(lines)
