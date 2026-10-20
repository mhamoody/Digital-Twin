"""Authenticated, course-scoped support workflow API."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from digital_twin.api.auth import require_instructor
from digital_twin.api.schemas import InstructorIdentity
from digital_twin.api.support_schemas import (CreateCase, SupportActionRequest,
    MutationResult, CaseList, CaseDetail)
from digital_twin.persistence.support import SupportStore

router=APIRouter(prefix="/api/v1",tags=["support"])


def workflow_dependency(request: Request, identity: Annotated[InstructorIdentity,Depends(require_instructor)]):
    service=request.app.state.api_service
    if service is None:
        raise HTTPException(503,"Database configuration is unavailable.")
    return SupportStore(service.engine,identity)

Workflow=Annotated[SupportStore,Depends(workflow_dependency)]

@router.get("/presentations/{presentation_id}/support-cases",response_model=CaseList)
def list_cases(presentation_id: str, workflow: Workflow,
               active: bool | None=None, follow_up_due: bool=False,
               limit: Annotated[int,Query(ge=1,le=200)]=50,
               offset: Annotated[int,Query(ge=0)]=0):
    return workflow.list(presentation_id,active=active,follow_up_due=follow_up_due,limit=limit,offset=offset)

@router.post("/presentations/{presentation_id}/support-cases",response_model=MutationResult)
def create_case(presentation_id: str, payload: CreateCase, workflow: Workflow):
    return workflow.create(presentation_id,payload)

@router.get("/support-cases/{case_id}",response_model=CaseDetail)
def get_case(case_id: str, workflow: Workflow):
    return workflow.detail(case_id)

@router.post("/support-cases/{case_id}/actions",response_model=MutationResult)
def record_action(case_id: str, payload: SupportActionRequest, workflow: Workflow):
    return workflow.act(case_id,payload)
