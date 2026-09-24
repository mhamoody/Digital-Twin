"""Transactional instructor workflow, independent of prediction writes."""
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from pydantic import TypeAdapter
from digital_twin.api.schemas import InstructorIdentity
from digital_twin.api.support_schemas import (CreateCase, SupportActionRequest, MutationResult,
    CaseView, ActionView, CaseDetail, CaseList, LinkedAlertView)
from digital_twin.api.service import ResourceNotFound, ReviewConflict
from .models import (SupportCase, SupportAction, SupportCaseAlert, Enrolment,
                     AlertRecord, PredictionRecord, WeeklyStateRecord, ModelVersion)
from .store import TwinStore, stable_hash

ACTIVE = ("new_concern", "reviewed", "ongoing")
OPERATIONAL_SCOPE = "operational"
TRANSITIONS = {
    "new_concern": {"reviewed", "ongoing", "resolved", "dismissed"},
    "reviewed": {"ongoing", "resolved", "dismissed"},
    "ongoing": {"ongoing", "resolved", "dismissed"},
    "resolved": set(), "dismissed": set(),
}
ACTION_ADAPTER = TypeAdapter(SupportActionRequest)


def view(model, row):
    return model(**{name: getattr(row, name) for name in model.model_fields})


class SupportStore:
    def __init__(self, engine, identity: InstructorIdentity, *, clock=None):
        self.engine = engine
        self.identity = identity
        self.grants = frozenset(identity.allowed_presentations)
        self.clock = clock or (lambda: datetime.now(UTC))

    def _authorize(self, presentation):
        if presentation not in self.grants:
            raise ResourceNotFound("Resource not found.")

    def _case(self, session, case_id):
        row = session.scalar(select(SupportCase).where(SupportCase.case_id == case_id,
            SupportCase.presentation_id.in_(self.grants)))
        if row is None:
            raise ResourceNotFound("Resource not found.")
        return row

    @staticmethod
    def _result(action):
        return MutationResult(case_id=action.case_id, action_id=action.action_id,
                              resulting_version=action.resulting_version)

    @staticmethod
    def _retry(action, request_hash):
        if action.request_hash != request_hash:
            raise ReviewConflict("Idempotency key already used for a different request.")
        return SupportStore._result(action)

    def _link(self, session, case, alert_id, now):
        row = session.execute(select(AlertRecord, WeeklyStateRecord, PredictionRecord)
            .join(WeeklyStateRecord, AlertRecord.state_id == WeeklyStateRecord.state_id)
            .join(PredictionRecord, AlertRecord.prediction_id == PredictionRecord.prediction_id)
            .join(ModelVersion, (PredictionRecord.model_ref == ModelVersion.model_ref)
                  & (ModelVersion.approved_scope == OPERATIONAL_SCOPE))
            .where(AlertRecord.alert_id == alert_id,
                   WeeklyStateRecord.presentation_id.in_(self.grants))).one_or_none()
        if row is None:
            raise ResourceNotFound("Resource not found.")
        alert, state, prediction = row
        if (state.presentation_id, state.learner_id, state.data_origin) != (
                case.presentation_id, case.learner_id, case.data_origin) or alert.data_origin != case.data_origin or prediction.data_origin != case.data_origin or prediction.state_id != state.state_id:
            raise ReviewConflict("Alert does not match the support enrolment.")
        link = session.scalar(select(SupportCaseAlert).where(SupportCaseAlert.alert_id == alert_id))
        if link:
            if link.case_id != case.case_id:
                raise ReviewConflict("Alert is already linked to a support episode.")
            return
        session.add(SupportCaseAlert(case_id=case.case_id, alert_id=alert_id,
                                    linked_at=now, link_reason="instructor_request"))

    def _record(self, session, case, payload, request_hash, now, *, action_type,
                previous_status=None, previous_due=None, creation_key=None):
        action = SupportAction(action_id="action:"+uuid4().hex, case_id=case.case_id,
            action_type=action_type, actor_id=self.identity.reviewer_id, actor_role=self.identity.role,
            created_at=now, idempotency_key=payload.idempotency_key, request_hash=request_hash,
            resulting_version=case.version, note=payload.note, previous_status=previous_status,
            new_status=case.status, previous_follow_up_due_at=previous_due,
            new_follow_up_due_at=case.follow_up_due_at,
            linked_alert_id=getattr(payload, "alert_id", None), creation_key=creation_key)
        session.add(action)
        session.flush()
        TwinStore(self.engine)._audit(session, None, "support_action", action.action_id,
                                     action_type, request_hash, now)
        return self._result(action)

    def _hash(self, payload, **scope):
        return stable_hash(dict(payload=payload.model_dump(mode="json"),
            actor=self.identity.reviewer_id, role=self.identity.role, **scope))

    def create(self, presentation_id, payload: CreateCase):
        payload = CreateCase.model_validate(payload.model_dump())
        self._authorize(presentation_id)
        request_hash = self._hash(payload, presentation=presentation_id)
        creation_key = stable_hash(dict(presentation=presentation_id, learner=payload.learner_id,
            actor=self.identity.reviewer_id, key=payload.idempotency_key))
        for attempt in range(3):
            try:
                with Session(self.engine) as session, session.begin():
                    prior = session.scalar(select(SupportAction).where(SupportAction.creation_key == creation_key))
                    if prior:
                        self._case(session, prior.case_id)
                        return self._retry(prior, request_hash)
                    enrolment = session.get(Enrolment, (presentation_id, payload.learner_id))
                    if enrolment is None:
                        raise ResourceNotFound("Resource not found.")
                    case = session.scalar(select(SupportCase).where(
                        SupportCase.presentation_id == presentation_id,
                        SupportCase.learner_id == payload.learner_id,
                        SupportCase.data_origin == enrolment.data_origin,
                        SupportCase.status.in_(ACTIVE)))
                    now = self.clock()
                    new = case is None
                    if new:
                        case = SupportCase(case_id="case:"+uuid4().hex, presentation_id=presentation_id,
                            learner_id=payload.learner_id, data_origin=enrolment.data_origin,
                            status="new_concern", opened_at=now,last_action_at=now,version=1,
                            created_by=self.identity.reviewer_id,created_by_role=self.identity.role)
                        session.add(case)
                        session.flush()
                        previous_status = None
                        previous_due = None
                    else:
                        collision = session.scalar(select(SupportAction).where(
                            SupportAction.case_id == case.case_id,
                            SupportAction.idempotency_key == payload.idempotency_key))
                        if collision:
                            return self._retry(collision, request_hash)
                        previous_status, previous_due = case.status, case.follow_up_due_at
                        result = session.execute(update(SupportCase).where(SupportCase.case_id==case.case_id,
                            SupportCase.version==case.version, SupportCase.status.in_(ACTIVE))
                            .values(version=case.version+1,last_action_at=now).execution_options(synchronize_session=False))
                        if result.rowcount != 1:
                            raise ReviewConflict("Case changed concurrently; retry creation.")
                        session.refresh(case)
                    if payload.alert_id:
                        self._link(session, case, payload.alert_id, now)
                    return self._record(session, case, payload, request_hash, now,
                        action_type="create_case" if new else "reuse_case", previous_status=previous_status,
                        previous_due=previous_due,creation_key=creation_key)
            except (IntegrityError, OperationalError) as error:
                if attempt == 2:
                    raise ReviewConflict("Concurrent or conflicting case creation; retry.") from error

    def act(self, case_id, payload):
        payload = ACTION_ADAPTER.validate_python(payload.model_dump())
        request_hash = self._hash(payload, case=case_id)
        for attempt in range(2):
            try:
                with Session(self.engine) as session, session.begin():
                    case = self._case(session, case_id)
                    prior = session.scalar(select(SupportAction).where(SupportAction.case_id==case_id,
                        SupportAction.idempotency_key==payload.idempotency_key))
                    if prior:
                        return self._retry(prior, request_hash)
                    if case.status not in ACTIVE:
                        raise ReviewConflict("Closed support cases are terminal.")
                    if case.version != payload.expected_version:
                        raise ReviewConflict("Stale case version.")
                    now = self.clock()
                    previous_status, previous_due = case.status, case.follow_up_due_at
                    values = dict(version=case.version+1,last_action_at=now)
                    if payload.action_type == "transition_status":
                        if payload.target_status not in TRANSITIONS[case.status]:
                            raise ReviewConflict("Invalid support status transition.")
                        values["status"] = payload.target_status
                        if payload.target_status not in ACTIVE:
                            values["closed_at"] = now
                    elif payload.action_type == "set_follow_up":
                        values["follow_up_due_at"] = payload.follow_up_due_at
                    elif payload.action_type == "clear_follow_up":
                        values["follow_up_due_at"] = None
                    result = session.execute(update(SupportCase).where(SupportCase.case_id==case_id,
                        SupportCase.version==payload.expected_version,SupportCase.status.in_(ACTIVE))
                        .values(**values).execution_options(synchronize_session=False))
                    if result.rowcount != 1:
                        raise ReviewConflict("Stale case version.")
                    session.refresh(case)
                    if payload.action_type == "link_alert":
                        self._link(session, case, payload.alert_id, now)
                    return self._record(session,case,payload,request_hash,now,
                        action_type=payload.action_type,previous_status=previous_status,previous_due=previous_due)
            except (IntegrityError, OperationalError) as error:
                if attempt == 1:
                    raise ReviewConflict("Concurrent or conflicting action; refresh and retry.") from error

    def detail(self, case_id):
        with Session(self.engine) as session:
            case = self._case(session, case_id)
            actions = session.scalars(select(SupportAction).where(SupportAction.case_id==case_id)
                .order_by(SupportAction.resulting_version, SupportAction.action_id)).all()
            links = session.execute(select(SupportCaseAlert,AlertRecord,WeeklyStateRecord,PredictionRecord)
                .join(AlertRecord,SupportCaseAlert.alert_id==AlertRecord.alert_id)
                .join(WeeklyStateRecord,AlertRecord.state_id==WeeklyStateRecord.state_id)
                .join(PredictionRecord,AlertRecord.prediction_id==PredictionRecord.prediction_id)
                .join(ModelVersion, (PredictionRecord.model_ref == ModelVersion.model_ref)
                      & (ModelVersion.approved_scope == OPERATIONAL_SCOPE))
                .where(SupportCaseAlert.case_id==case_id).order_by(SupportCaseAlert.linked_at,SupportCaseAlert.alert_id)).all()
            return CaseDetail(case=view(CaseView,case), actions=[view(ActionView,a) for a in actions],
                linked_alerts=[LinkedAlertView(alert_id=a.alert_id,prediction_id=p.prediction_id,
                    state_id=s.state_id,checkpoint=s.checkpoint_week,risk_band=p.risk_band,
                    linked_at=l.linked_at,link_reason=l.link_reason) for l,a,s,p in links])

    def list(self, presentation_id, *, active=None, follow_up_due=False, limit=50, offset=0):
        self._authorize(presentation_id)
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("Invalid pagination")
        conditions = [SupportCase.presentation_id==presentation_id]
        if active is not None:
            conditions.append(SupportCase.status.in_(ACTIVE) if active else SupportCase.status.not_in(ACTIVE))
        if follow_up_due:
            conditions.extend([SupportCase.status.in_(ACTIVE),SupportCase.follow_up_due_at<=self.clock()])
        with Session(self.engine) as session:
            total = session.scalar(select(func.count()).select_from(SupportCase).where(*conditions))
            rows = session.scalars(select(SupportCase).where(*conditions)
                .order_by(SupportCase.opened_at,SupportCase.case_id).offset(offset).limit(limit)).all()
            return CaseList(items=[view(CaseView,c) for c in rows],total=total,limit=limit,offset=offset)
