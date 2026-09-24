"""Judge adapters."""

from __future__ import annotations

from .base import JudgeAdapter, JudgeConfig, RawJudgeResponse
from .fake import FakeJudgeAdapter
from .http import HttpJudgeAdapter

__all__ = [
    "FakeJudgeAdapter",
    "HttpJudgeAdapter",
    "JudgeAdapter",
    "JudgeConfig",
    "RawJudgeResponse",
]
