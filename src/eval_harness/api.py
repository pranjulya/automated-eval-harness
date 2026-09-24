"""Thin authenticated HTTP API over the shared application services.

Routes translate HTTP into the same `RunService` / `CompareService` /
`PromotionService` calls the CLI uses. There is no evaluation, gate, or
persistence logic here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, JsonValue

from .api_auth import Principal, Role, TokenVerifier, require_role
from .application.compare import CompareService
from .application.online import OnlineSampler
from .application.promote import PromotionService
from .application.run import RunConfig, RunRequest, RunService
from .domain.cases import Profile
from .domain.gates import GatePolicy
from .domain.runs import Summary
from .errors import HarnessError

__all__ = ["create_app"]

READ_ROLES = (Role.READER, Role.RUNNER, Role.QUALITY_OWNER, Role.SECURITY_ADMIN)
RUN_ROLES = (Role.RUNNER, Role.QUALITY_OWNER, Role.SECURITY_ADMIN)
OWNER_ROLES = (Role.QUALITY_OWNER, Role.SECURITY_ADMIN)
SECURITY_ROLES = (Role.SECURITY_ADMIN,)


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suite_path: str
    profile: str | None = None
    tag: str | None = None
    run_id: str | None = None


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_run_id: str
    suite: str
    channel: str


class PromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    reason: str
    approval_evidence: tuple[str, ...] = ()
    policy_path: str = "evaluation/configs/gate-policy-v1.json"


class SampleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: str
    tenant: str
    consent: bool
    classification: str
    payload: JsonValue = None


class SampleReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accept: bool
    note: str = ""


class SampleDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str


_STATUS_BY_CODE = {
    "UNAUTHENTICATED": 401,
    "FORBIDDEN": 403,
    "SAMPLE_NOT_FOUND": 404,
    "SAMPLE_EXPIRED": 409,
    "SAMPLE_NOT_ELIGIBLE": 409,
    "CONSENT_REQUIRED": 400,
    "CONFIG_INVALID": 400,
    "DATASET_INVALID": 400,
    "CLI_USAGE": 400,
}


def _status_for(code: str) -> int:
    return _STATUS_BY_CODE.get(code, 500)


def _summary_for(store: Any, run_id: str) -> Summary:
    store.read_bundle(run_id)
    return Summary.model_validate_json(
        (store.run_dir(run_id) / "summary.json").read_text(encoding="utf-8")
    )


def create_app(
    *,
    store: Any,
    run_service: RunService,
    compare_service: CompareService,
    promotion_service: PromotionService,
    verifier: TokenVerifier,
    sampler: OnlineSampler,
    policy: GatePolicy,
    default_run_config: RunConfig,
) -> FastAPI:
    app = FastAPI(title="eval-harness", version="0.1.0")
    bearer = HTTPBearer(auto_error=False)
    idempotency: dict[str, dict[str, Any]] = {}

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
        if credentials is None:
            raise HarnessError("missing bearer token", code="UNAUTHENTICATED")
        return verifier.verify(credentials.credentials)

    @app.exception_handler(HarnessError)
    async def _harness_error(_request: Request, exc: HarnessError) -> JSONResponse:
        return JSONResponse(
            status_code=_status_for(exc.code),
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "retryable": exc.retryable,
                    "correlation_id": getattr(_request.state, "correlation_id", ""),
                    "details": exc.details,
                }
            },
        )

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready() -> dict[str, Any]:
        try:
            store.list_runs()
            artifacts_ready = True
        except Exception:
            artifacts_ready = False
        return {"status": "ready" if artifacts_ready else "degraded", "artifacts": artifacts_ready}

    @app.post("/v1/runs", status_code=202)
    def create_run(
        body: RunCreateRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        user: Principal = Depends(principal),
    ) -> dict[str, Any]:
        require_role(user, *RUN_ROLES)
        if idempotency_key and idempotency_key in idempotency:
            return idempotency[idempotency_key]
        profile = body.profile
        request = RunRequest(
            suite_path=Path(body.suite_path),
            config=default_run_config,
            profile=Profile(profile) if profile else None,
            tag=body.tag,
            run_id=body.run_id,
        )
        outcome = run_service.run(request)
        response = {
            "run_id": outcome.run_id,
            "status": str(outcome.status),
            "summary": outcome.summary.model_dump(mode="json"),
        }
        if idempotency_key:
            idempotency[idempotency_key] = response
        return response

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str, user: Principal = Depends(principal)) -> dict[str, Any]:
        require_role(user, *READ_ROLES)
        manifest = store.read_manifest(run_id)
        summary = _summary_for(store, run_id)
        return {
            "manifest": manifest.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
        }

    @app.get("/v1/runs/{run_id}/cases")
    def get_cases(
        run_id: str,
        profile: str | None = None,
        state: str | None = None,
        user: Principal = Depends(principal),
    ) -> dict[str, Any]:
        require_role(user, *READ_ROLES)
        store.read_bundle(run_id)
        cases = [
            json.loads(line)
            for line in (store.run_dir(run_id) / "cases.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        if profile:
            cases = [case for case in cases if case["primary_profile"] == profile]
        if state:
            cases = [case for case in cases if case["state"] == state]
        return {"run_id": run_id, "cases": cases}

    @app.post("/v1/comparisons")
    def compare(body: ComparisonRequest, user: Principal = Depends(principal)) -> dict[str, Any]:
        require_role(user, *READ_ROLES)
        comparison = compare_service.compare(
            body.candidate_run_id, body.suite, body.channel, policy
        )
        return comparison.model_dump(mode="json")

    @app.get("/v1/baselines/{suite}/{channel}")
    def get_baseline(
        suite: str, channel: str, user: Principal = Depends(principal)
    ) -> dict[str, Any]:
        require_role(user, *READ_ROLES)
        record = store.read_baseline(suite, channel)
        return cast(dict[str, Any], record.model_dump(mode="json"))

    @app.post("/v1/baselines/{suite}/{channel}/promotions")
    def promote(
        suite: str, channel: str, body: PromotionRequest, user: Principal = Depends(principal)
    ) -> dict[str, Any]:
        require_role(user, *OWNER_ROLES)
        from .application.compare import load_policy
        from .domain.baselines import PromotionAuthorization

        policy_value = load_policy(Path(body.policy_path))
        authorization = PromotionAuthorization(
            actor=user.actor,  # server-derived actor, never from the body
            approval_evidence=body.approval_evidence or (f"github:{user.actor}",),
            reason=body.reason,
        )
        record = promotion_service.promote(
            body.run_id, suite, channel, authorization, policy_value.policy_hash()
        )
        return record.model_dump(mode="json")

    @app.get("/v1/samples")
    def list_samples(user: Principal = Depends(principal)) -> dict[str, Any]:
        require_role(user, *OWNER_ROLES)
        return {"samples": [candidate.model_dump(mode="json") for candidate in sampler.list()]}

    @app.post("/v1/samples", status_code=201)
    def create_sample(
        body: SampleCreateRequest, user: Principal = Depends(principal)
    ) -> dict[str, Any]:
        require_role(user, *RUN_ROLES)
        candidate = sampler.submit(
            sample_id=body.sample_id,
            tenant=body.tenant,
            consent=body.consent,
            classification=body.classification,
            payload=body.payload,
        )
        return candidate.model_dump(mode="json")

    @app.post("/v1/samples/{sample_id}/review")
    def review_sample(
        sample_id: str, body: SampleReviewRequest, user: Principal = Depends(principal)
    ) -> dict[str, Any]:
        require_role(user, *OWNER_ROLES)
        candidate = sampler.review(sample_id, user.actor, accept=body.accept, note=body.note)
        return candidate.model_dump(mode="json")

    @app.get("/v1/samples/{sample_id}/draft")
    def sample_draft(sample_id: str, user: Principal = Depends(principal)) -> dict[str, Any]:
        require_role(user, *OWNER_ROLES)
        return sampler.propose_draft_case(sample_id)

    @app.delete("/v1/samples/{sample_id}")
    def delete_sample(
        sample_id: str, body: SampleDeleteRequest, user: Principal = Depends(principal)
    ) -> dict[str, Any]:
        require_role(user, *SECURITY_ROLES)
        evidence = sampler.delete(sample_id, user.actor, body.reason)
        return evidence.model_dump(mode="json")

    return app
