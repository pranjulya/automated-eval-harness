"""Strict, discriminated golden-case contracts (schema ``eval.case.v1``)."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    field_validator,
    model_validator,
)

__all__ = [
    "CASE_ID_PATTERN",
    "PROFILE_PREFIX",
    "TAG_VOCABULARY",
    "EvalCase",
    "Outcome",
    "Profile",
    "parse_case",
    "validate_case_id",
]

SCHEMA_VERSION: Literal["eval.case.v1"] = "eval.case.v1"

TAG_VOCABULARY: frozenset[str] = frozenset(
    {
        "factual",
        "normalization",
        "synthesis",
        "ambiguity",
        "refusal",
        "injection",
        "canary",
        "schema",
        "extra-fields",
        "business-rule",
        "lexical",
        "semantic-retrieval",
        "distractor",
        "multi-document",
        "citation",
        "no-answer",
        "isolation",
        "tool-selection",
        "tool-arguments",
        "tool-order",
        "termination",
        "forbidden-action",
    }
)

CASE_ID_PATTERN = re.compile(r"^(?P<prefix>text|safe|struct|rag|tool)-\d{3}$")


class Profile(StrEnum):
    TEXT_SEMANTIC = "text_semantic"
    SAFETY_ABSTENTION = "safety_abstention"
    STRUCTURED_OUTPUT = "structured_output"
    RAG = "rag"
    TOOL_USE = "tool_use"


PROFILE_PREFIX: dict[Profile, str] = {
    Profile.TEXT_SEMANTIC: "text",
    Profile.SAFETY_ABSTENTION: "safe",
    Profile.STRUCTURED_OUTPUT: "struct",
    Profile.RAG: "rag",
    Profile.TOOL_USE: "tool",
}

Outcome = Literal["answered", "refused", "insufficient_evidence"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Message(_Strict):
    role: Literal["system", "user", "assistant"]
    content: str


class CaseInput(_Strict):
    messages: tuple[Message, ...] = Field(min_length=1)
    attachments: tuple[str, ...] = ()
    variables: dict[str, str] = Field(default_factory=dict)


class Limits(_Strict):
    timeout_ms: int = Field(gt=0)
    max_output_bytes: int = Field(gt=0)


class Provenance(_Strict):
    author: str
    reviewers: tuple[str, ...] = Field(min_length=1)
    source_classification: Literal["synthetic"]
    rationale: str


class SemanticSpec(_Strict):
    rubric_id: str
    reference_answer: str | None = None
    dimensions: tuple[str, ...] = ()


class EvidenceLabel(_Strict):
    document_id: str
    evidence_id: str
    grade: int = Field(ge=0, le=2)


class Assertion(_Strict):
    pointer: str
    op: Literal["equals", "exists", "type", "enum", "range", "length"]
    value: JsonValue = None
    minimum: float | None = None
    maximum: float | None = None
    expects: bool = True


class ToolDef(_Strict):
    name: str
    version: str


class ToolCallExpectation(_Strict):
    name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    exact: bool = True


class TextDeterministic(_Strict):
    kind: Literal["text"] = "text"
    required_values: tuple[str, ...] = ()
    forbidden_values: tuple[str, ...] = ()
    normalized_match: bool = True
    trusted_regex: tuple[str, ...] = ()


class SafetyDeterministic(_Strict):
    kind: Literal["safety"] = "safety"
    required_outcome: Outcome
    forbidden_patterns: tuple[str, ...] = ()
    canaries: tuple[str, ...] = ()


class StructuredDeterministic(_Strict):
    kind: Literal["structured"] = "structured"
    json_schema_id: str
    assertions: tuple[Assertion, ...] = ()


class RagDeterministic(_Strict):
    kind: Literal["rag"] = "rag"
    answerable: bool
    relevant_evidence: tuple[EvidenceLabel, ...] = ()
    recall_k: tuple[int, ...] = ()
    required_citation_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _answerability_consistent(self) -> RagDeterministic:
        if self.answerable and not self.relevant_evidence:
            raise ValueError("answerable RAG case requires relevant_evidence")
        if not self.answerable and self.relevant_evidence:
            raise ValueError("unanswerable RAG case must not declare relevant_evidence")
        return self


class ToolDeterministic(_Strict):
    kind: Literal["tool"] = "tool"
    allowed_tools: tuple[ToolDef, ...] = Field(min_length=1)
    expected_calls: tuple[ToolCallExpectation, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    max_steps: int = Field(gt=0)
    require_termination: bool = True


class TextExpectation(_Strict):
    outcome: Outcome
    deterministic: TextDeterministic
    semantic: SemanticSpec | None = None


class SafetyExpectation(_Strict):
    outcome: Outcome
    deterministic: SafetyDeterministic
    semantic: SemanticSpec | None = None


class StructuredExpectation(_Strict):
    outcome: Outcome
    deterministic: StructuredDeterministic
    semantic: SemanticSpec | None = None


class RagExpectation(_Strict):
    outcome: Outcome
    deterministic: RagDeterministic
    semantic: SemanticSpec | None = None


class ToolExpectation(_Strict):
    outcome: Outcome
    deterministic: ToolDeterministic
    semantic: SemanticSpec | None = None


class _CaseBase(_Strict):
    schema_version: Literal["eval.case.v1"] = SCHEMA_VERSION
    case_id: str
    title: str = Field(min_length=1)
    primary_profile: Profile
    tags: tuple[str, ...] = ()
    weight: int = 1
    input: CaseInput
    limits: Limits
    provenance: Provenance

    @field_validator("tags")
    @classmethod
    def _known_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = sorted(set(value) - TAG_VOCABULARY)
        if unknown:
            raise ValueError(f"unknown tags: {unknown}")
        if len(set(value)) != len(value):
            raise ValueError("duplicate tags are not allowed")
        return value

    @model_validator(mode="after")
    def _check_case_identity(self) -> _CaseBase:
        match = CASE_ID_PATTERN.match(self.case_id)
        if match is None:
            raise ValueError("case_id must match ^(text|safe|struct|rag|tool)-\\d{3}$")
        expected = PROFILE_PREFIX[self.primary_profile]
        if match.group("prefix") != expected:
            raise ValueError(f"case_id prefix must be '{expected}' for this profile")
        if self.weight != 1:
            raise ValueError("V1 case weight must be 1")
        return self


class TextCase(_CaseBase):
    primary_profile: Literal[Profile.TEXT_SEMANTIC] = Profile.TEXT_SEMANTIC
    expectation: TextExpectation


class SafetyCase(_CaseBase):
    primary_profile: Literal[Profile.SAFETY_ABSTENTION] = Profile.SAFETY_ABSTENTION
    expectation: SafetyExpectation


class StructuredCase(_CaseBase):
    primary_profile: Literal[Profile.STRUCTURED_OUTPUT] = Profile.STRUCTURED_OUTPUT
    expectation: StructuredExpectation


class RagCase(_CaseBase):
    primary_profile: Literal[Profile.RAG] = Profile.RAG
    expectation: RagExpectation


class ToolCase(_CaseBase):
    primary_profile: Literal[Profile.TOOL_USE] = Profile.TOOL_USE
    expectation: ToolExpectation


EvalCase = Annotated[
    TextCase | SafetyCase | StructuredCase | RagCase | ToolCase,
    Field(discriminator="primary_profile"),
]

_CASE_ADAPTER: TypeAdapter[EvalCase] = TypeAdapter(EvalCase)


def parse_case(data: object) -> EvalCase:
    """Parse one untrusted case object into a strict, discriminated case."""

    return _CASE_ADAPTER.validate_python(data)


def validate_case_id(case_id: str) -> bool:
    return CASE_ID_PATTERN.match(case_id) is not None
