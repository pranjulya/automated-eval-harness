"""Load suite JSON Schemas by identifier for the structured evaluator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import SchemaResolver

__all__ = ["load_schema_resolver"]


def load_schema_resolver(root: Path) -> SchemaResolver:
    """Return a resolver that maps ``schema:<name>`` to ``evaluation/schemas/<name>.json``."""

    def resolve(schema_id: str) -> dict[str, Any] | None:
        if not schema_id.startswith("schema:"):
            return None
        path = Path(root) / "evaluation" / "schemas" / f"{schema_id.split(':', 1)[1]}.json"
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None

    return resolve
