"""Authenticated v2 routes. Browser input selects stored snapshots, never evidence."""

from __future__ import annotations

import os
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from digital_twin.api.auth import authorize_course, require_instructor
from digital_twin.api.schemas import InstructorIdentity

from .contracts import CaseUpdate, Contract, CoursePolicy, digest
from .scheduling import runtime_spec
from .store import Conflict, Store

router = APIRouter(prefix="/api/v2", tags=["workspace"])
Identity = Annotated[InstructorIdentity, Depends(require_instructor)]


def get_store(request: Request):
    service = request.app.state.api_service
    if service is None:
        raise HTTPException(503, "Database configuration is unavailable.")
    return Store(service.engine)


Storage = Annotated[Store, Depends(get_store)]


def checked(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except (Conflict, IntegrityError) as error:
        raise HTTPException(409, "A concurrent update occurred. Refresh and retry.") from error
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            503,
            "Workspace database unavailable. "
            "Ask the operator to check migrations and service health.",
        ) from error


@router.get("/courses")
def courses(identity: Identity, store: Storage):
    return {"items": checked(store.courses, identity.allowed_presentations)}


@router.get("/courses/{course_id}/workspace")
def workspace(
    course_id: str,
    identity: Identity,
    store: Storage,
    week: int = Query(ge=1, le=60),
    query: str = Query(default="", max_length=128),
    risk: str = "",
    status: str = "",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    authorize_course(identity, course_id)
    return checked(store.workspace, course_id, week, query, risk, status, offset, limit)


@router.get("/courses/{course_id}/learners/{learner_id}")
def learner(
    course_id: str,
    learner_id: str,
    identity: Identity,
    store: Storage,
    week: int = Query(ge=1, le=60),
):
    authorize_course(identity, course_id)
    return checked(store.learner, course_id, learner_id, week)


@router.post("/courses/{course_id}/policy")
def policy(course_id: str, change: CoursePolicy, identity: Identity, store: Storage):
    authorize_course(identity, course_id)
    return {
        "policy": checked(store.set_policy, course_id, change, identity.reviewer_id).model_dump(
            mode="json"
        )
    }


@router.post("/courses/{course_id}/learners/{learner_id}/case")
def support_case(
    course_id: str,
    learner_id: str,
    change: CaseUpdate,
    identity: Identity,
    store: Storage,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
):
    authorize_course(identity, course_id)
    return checked(
        store.update_case, course_id, learner_id, change, identity.reviewer_id, idempotency_key
    )


class AnalysisRequest(Contract):
    week: int = Field(ge=1, le=60)
    learner_ids: list[str] | None = Field(default=None, min_length=1, max_length=5000)
    model_kind: Literal["llm", "baseline"] = "llm"


@router.post("/courses/{course_id}/analysis", status_code=202)
def analysis(course_id: str, request: AnalysisRequest, identity: Identity, store: Storage):
    authorize_course(identity, course_id)
    from .llm import PROMPT_VERSION

    expected_digest = None
    if request.model_kind == "llm":
        return checked(
            store.queue_analysis,
            course_id,
            checked(runtime_spec),
            week=request.week,
            learner_ids=request.learner_ids,
        )
    fingerprint = digest(
        [
            os.environ.get("DIGITAL_TWIN_LLM_MODEL", "qwen2.5:7b"),
            os.environ.get("DIGITAL_TWIN_LLM_DIGEST", ""),
            PROMPT_VERSION,
            os.environ.get("DIGITAL_TWIN_LLM_CONTEXT", "8192"),
            os.environ.get("DIGITAL_TWIN_LLM_MAX_TOKENS", "1200"),
        ]
    )
    jobs = checked(
        store.enqueue,
        course_id,
        request.week,
        request.learner_ids,
        request.model_kind,
        fingerprint,
        expected_digest,
    )
    return {"job_ids": jobs, "queued": len(jobs)}


class BatchAnalysisRequest(Contract):
    scope: Literal["all_weeks", "week"] = "all_weeks"
    week: int | None = Field(default=None, ge=1, le=60)
    mode: Literal["unassessed", "retry_failed"] = "unassessed"


class AutomationRequest(Contract):
    enabled: bool = Field(strict=True)
    version: int = Field(ge=1)


@router.get("/courses/{course_id}/analysis/status")
def analysis_status(course_id: str, identity: Identity, store: Storage):
    authorize_course(identity, course_id)
    return checked(store.analysis_status, course_id, checked(runtime_spec))


@router.post("/courses/{course_id}/analysis/batch", status_code=202)
def analysis_batch(
    course_id: str, change: BatchAnalysisRequest, identity: Identity, store: Storage
):
    authorize_course(identity, course_id)
    if (change.scope == "week") != (change.week is not None):
        raise HTTPException(422, "Specify a week only for the single-checkpoint scope.")
    return checked(
        store.queue_analysis, course_id, checked(runtime_spec), week=change.week, mode=change.mode
    )


@router.post("/courses/{course_id}/analysis/automation")
def automation(course_id: str, change: AutomationRequest, identity: Identity, store: Storage):
    authorize_course(identity, course_id)
    return checked(
        store.set_automation, course_id, change.enabled, change.version, identity.reviewer_id
    )


@router.post("/courses/{course_id}/analysis/resume")
def resume(course_id: str, identity: Identity, store: Storage):
    authorize_course(identity, course_id)
    return checked(store.resume_analysis, course_id, identity.reviewer_id)


@router.get("/model/status")
def model_status(identity: Identity, store: Storage):
    from .llm import OllamaClient

    try:
        client = OllamaClient()
        result = client.readiness()
    except Exception:
        result = {
            "status": "unavailable",
            "model": os.environ.get("DIGITAL_TWIN_LLM_MODEL", "qwen2.5:7b"),
        }
    return result
