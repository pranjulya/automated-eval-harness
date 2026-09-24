"""Report projections (Markdown now, HTML/CSV later)."""

from __future__ import annotations

from .json_report import summary_payload
from .markdown import render_report

__all__ = ["render_report", "summary_payload"]
