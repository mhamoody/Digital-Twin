"""FastAPI application factory for the instructor-facing vertical slice."""

from __future__ import annotations

import hashlib
import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from digital_twin.persistence import create_twin_engine

from .auth import authorize_course, require_instructor
from .schemas import (
    AlertDetail,
    AlertListResponse,
    AlertReviewRequest,
    AlertReviewResponse,
    ApiError,
    HealthResponse,
    InstructorIdentity,
    LearnerDetailResponse,
    LearnerListResponse,
    PresentationOverview,
)
from .service import ApiService, ResourceNotFound, ReviewConflict

API_DESCRIPTION = """
Instructor-facing boundary for the course digital-twin integration demo.

All course, learner, alert, prediction, evidence, and review endpoints require
an instructor identity. Local LMS plugins can use the short-lived HMAC-signed
header profile; the older `X-Instructor-ID` and `X-Instructor-Role` pair remains
a development-only fallback. Queen's onQ deployment must use validated LTI 1.3
launch identity rather than either local profile. The API never exposes final
outcomes, restricted fairness attributes, direct student identifiers, or
unrestricted educational text.
"""


def service_dependency(request: Request) -> ApiService:
    service = request.app.state.api_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database configuration is unavailable.",
        )
    return service


ServiceDependency = Annotated[ApiService, Depends(service_dependency)]
IdentityDependency = Annotated[InstructorIdentity, Depends(require_instructor)]


class LLMStateIn(BaseModel):
    week: int
    engagement_score: float
    active_days: int
    missed_assessments: int
    activity_trend: str
    evidence_ids: list[str]


class LLMEvalRequest(BaseModel):
    model_name: str
    state: LLMStateIn


def create_app(*, database_url: str | None = None, engine: Engine | None = None) -> FastAPI:
    app = FastAPI(
        title="Course Digital Twin Instructor API",
        version="0.1.0-phase4",
        description=API_DESCRIPTION,
    )
    configured_engine = engine
    if configured_engine is None:
        effective_url = database_url or os.environ.get("DIGITAL_TWIN_DATABASE_URL")
        if effective_url:
            configured_engine = create_twin_engine(effective_url)
    app.state.api_service = ApiService(configured_engine) if configured_engine else None

    @app.middleware("http")
    async def protect_sensitive_responses(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            body = await request.body()
            if len(body) > 1_000_000:
                return JSONResponse(status_code=413, content={"detail": "Request is too large."})
            request.state.body_hash = hashlib.sha256(body).hexdigest()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ResourceNotFound)
    async def not_found_handler(_request: Request, error: ResourceNotFound) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Resource not found: {error}"},
        )

    @app.exception_handler(ReviewConflict)
    async def conflict_handler(_request: Request, error: ReviewConflict) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(error)},
        )

    @app.get("/health/live", response_model=HealthResponse, tags=["health"])
    def liveness() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/health/ready",
        response_model=HealthResponse,
        responses={503: {"model": HealthResponse}},
        tags=["health"],
    )
    def readiness(request: Request):
        service = request.app.state.api_service
        if service is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=HealthResponse(status="not_ready").model_dump(mode="json"),
            )
        try:
            backend, revision = service.readiness()
        except (SQLAlchemyError, LookupError):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=HealthResponse(
                    status="not_ready", database_backend=service.engine.dialect.name
                ).model_dump(mode="json"),
            )
        return HealthResponse(status="ok", database_backend=backend, migration_revision=revision)

    @app.post("/api/v1/llm/evaluate", tags=["llm"])
    def llm_evaluate(payload: LLMEvalRequest, _identity: IdentityDependency):
        raise HTTPException(
            410, "The experimental endpoint is retired. Use the course-scoped v2 analysis jobs."
        )

    @app.get(
        "/api/v1/presentations/{presentation_id}/overview",
        response_model=PresentationOverview,
        responses={401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError}},
        tags=["presentations"],
    )
    def get_presentation_overview(
        presentation_id: str,
        service: ServiceDependency,
        _identity: IdentityDependency,
    ) -> PresentationOverview:
        authorize_course(_identity, presentation_id)
        return service.presentation_overview(presentation_id)

    @app.get(
        "/api/v1/presentations/{presentation_id}/learners",
        response_model=LearnerListResponse,
        responses={401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError}},
        tags=["learners"],
    )
    def get_presentation_learners(
        presentation_id: str,
        service: ServiceDependency,
        _identity: IdentityDependency,
        query: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> LearnerListResponse:
        authorize_course(_identity, presentation_id)
        return service.list_learners(
            presentation_id=presentation_id,
            query=query,
            limit=limit,
            offset=offset,
        )

    @app.get(
        "/api/v1/presentations/{presentation_id}/learners/{learner_id}",
        response_model=LearnerDetailResponse,
        responses={401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError}},
        tags=["learners"],
    )
    def get_presentation_learner_detail(
        presentation_id: str,
        learner_id: str,
        service: ServiceDependency,
        _identity: IdentityDependency,
    ) -> LearnerDetailResponse:
        authorize_course(_identity, presentation_id)
        return service.learner_detail(
            presentation_id=presentation_id,
            learner_id=learner_id,
        )

    @app.get(
        "/api/v1/alerts",
        response_model=AlertListResponse,
        responses={401: {"model": ApiError}, 403: {"model": ApiError}},
        tags=["alerts"],
    )
    def get_alerts(
        service: ServiceDependency,
        _identity: IdentityDependency,
        presentation_id: Annotated[str | None, Query(max_length=128)] = None,
        alert_status: Annotated[
            str | None,
            Query(alias="status", pattern="^(new|reviewed|resolved|dismissed)$"),
        ] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> AlertListResponse:
        authorize_course(_identity, presentation_id)
        return service.list_alerts(
            presentation_id=presentation_id,
            alert_status=alert_status,
            limit=limit,
            offset=offset,
        )

    @app.get(
        "/api/v1/alerts/{alert_id}",
        response_model=AlertDetail,
        responses={401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError}},
        tags=["alerts"],
    )
    def get_alert_detail(
        alert_id: str,
        service: ServiceDependency,
        _identity: IdentityDependency,
    ) -> AlertDetail:
        detail = service.alert_detail(alert_id)
        authorize_course(_identity, detail.alert.presentation_id)
        return detail

    @app.post(
        "/api/v1/alerts/{alert_id}/reviews",
        response_model=AlertReviewResponse,
        responses={
            400: {"model": ApiError},
            401: {"model": ApiError},
            403: {"model": ApiError},
            404: {"model": ApiError},
            409: {"model": ApiError},
        },
        tags=["reviews"],
    )
    def post_alert_review(
        alert_id: str,
        payload: AlertReviewRequest,
        service: ServiceDependency,
        identity: IdentityDependency,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> AlertReviewResponse:
        authorize_course(identity, service.alert_detail(alert_id).alert.presentation_id)
        if not idempotency_key or not 8 <= len(idempotency_key) <= 128:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key must contain between 8 and 128 characters.",
            )
        return service.review_alert(
            alert_id=alert_id,
            identity_id=identity.reviewer_id,
            identity_role=identity.role,
            idempotency_key=idempotency_key,
            request=payload,
        )

    def phase4_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                security = operation.get("security")
                scheme_names = {name for requirement in security or [] for name in requirement}
                if scheme_names == {"InstructorIdentity", "InstructorRole"}:
                    operation["security"] = [{"InstructorIdentity": [], "InstructorRole": []}]
        app.openapi_schema = schema
        return schema

    from digital_twin.workspace.api import router as workspace_router

    app.include_router(workspace_router)
    app.openapi = phase4_openapi
    return app


app = create_app()
