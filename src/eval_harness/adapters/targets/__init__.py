"""Target adapters."""

from __future__ import annotations

from .base import AttemptResult, TargetAdapter, TargetConfig, TargetIdentity
from .fake import FakeTargetAdapter, load_fake_responses
from .http import HttpTargetAdapter

__all__ = [
    "AttemptResult",
    "FakeTargetAdapter",
    "HttpTargetAdapter",
    "TargetAdapter",
    "TargetConfig",
    "TargetIdentity",
    "load_fake_responses",
]
