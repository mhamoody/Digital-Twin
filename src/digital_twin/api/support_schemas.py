"""Typed instructor-authored workflow requests; never model evidence."""
from datetime import UTC
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, field_validator
from .schemas import ApiContract

Key = Annotated[str, Field(min_length=8, max_length=128)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]
Note = Annotated[str, Field(min_length=1, max_length=4000)]
Status = Literal["new_concern", "reviewed", "ongoing", "resolved", "dismissed"]

class CreateCase(ApiContract):
    learner_id: Identifier
    alert_id: Identifier | None = None
    idempotency_key: Key
    note: Note | None = None

class ActionBase(ApiContract):
    expected_version: int = Field(ge=1)
    idempotency_key: Key

class AddNote(ActionBase):
    action_type: Literal["add_note"]
    note: Note

class Transition(ActionBase):
    action_type: Literal["transition_status"]
    target_status: Status
    note: Note | None = None

class SetFollowUp(ActionBase):
    action_type: Literal["set_follow_up"]
    follow_up_due_at: AwareDatetime
    note: Note | None = None

    @field_validator("follow_up_due_at")
    @classmethod
    def normalize_due_time(cls, value):
        return value.astimezone(UTC)

class ClearFollowUp(ActionBase):
    action_type: Literal["clear_follow_up"]
    note: Note | None = None

class LinkAlert(ActionBase):
    action_type: Literal["link_alert"]
    alert_id: Identifier
    note: Note | None = None

SupportActionRequest = Annotated[AddNote | Transition | SetFollowUp | ClearFollowUp | LinkAlert,
                               Field(discriminator="action_type")]

class MutationResult(ApiContract):
    case_id: str
    action_id: str
    resulting_version: int

class CaseView(ApiContract):
    case_id: str
    presentation_id: str
    learner_id: str
    data_origin: str
    status: Status
    opened_at: AwareDatetime
    last_action_at: AwareDatetime
    follow_up_due_at: AwareDatetime | None
    closed_at: AwareDatetime | None
    version: int
    created_by: str
    created_by_role: str

class LinkedAlertView(ApiContract):
    alert_id: str
    prediction_id: str
    state_id: str
    checkpoint: int
    risk_band: str | None
    linked_at: AwareDatetime
    link_reason: str

class ActionView(ApiContract):
    action_id: str
    case_id: str
    action_type: str
    actor_id: str
    actor_role: str
    created_at: AwareDatetime
    resulting_version: int
    note: str | None
    previous_status: str | None
    new_status: str | None
    previous_follow_up_due_at: AwareDatetime | None
    new_follow_up_due_at: AwareDatetime | None
    linked_alert_id: str | None

class CaseDetail(ApiContract):
    case: CaseView
    linked_alerts: list[LinkedAlertView]
    actions: list[ActionView]

class CaseList(ApiContract):
    items: list[CaseView]
    total: int
    limit: int
    offset: int
