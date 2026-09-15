"""Durable snapshots, versioned course policy, inference jobs and support cases."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .contracts import CaseUpdate, CoursePolicy, LearnerSnapshot, ModelOutput, digest
from .controls import save_control
from .errors import describe_failure
from .models import (
    Analysis,
    AnalysisAttempt,
    AnalysisJob,
    AnalysisPlan,
    CaseEvent,
    Course,
    CourseAnalysisControl,
    Enrolment,
    Event,
    Policy,
    Snapshot,
    SnapshotHead,
    SupportCase,
)
from .scheduling import MAX_ATTEMPTS, SchedulingMixin, register_heads
from .tracing import persist_traces, safe_attempts


class Conflict(ValueError):
    pass


def now():
    return datetime.now(UTC)


def payload(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


class Store(SchedulingMixin):
    def __init__(self, engine):
        self.engine = engine

    def ingest_dataset(self, dataset: dict) -> dict:
        """Idempotent import. Existing IDs must match exactly; never overwrite evidence."""
        counts = {}
        with Session(self.engine) as session, session.begin():
            mappings = [
                (Course, [{"id": x["presentation_id"], "payload": x} for x in dataset["courses"]]),
                (
                    Enrolment,
                    [
                        {
                            "course_id": x["presentation_id"],
                            "learner_id": x["learner_id"],
                            "payload": x,
                        }
                        for x in dataset["enrolments"]
                    ],
                ),
                (
                    Event,
                    [
                        {
                            "id": x["event_id"],
                            "course_id": x["presentation_id"],
                            "learner_id": x["learner_id"],
                            "course_day": x["course_day"],
                            "available_day": x["available_day"],
                            "payload": x,
                        }
                        for x in dataset.get("events", [])
                    ],
                ),
            ]
            states = [LearnerSnapshot.model_validate(payload(x)) for x in dataset["snapshots"]]
            mappings.append(
                (
                    Snapshot,
                    [
                        {
                            "id": x.state_id,
                            "course_id": x.presentation_id,
                            "learner_id": x.learner_id,
                            "week": x.checkpoint_week,
                            "input_hash": digest(x),
                            "payload": payload(x),
                        }
                        for x in states
                    ],
                )
            )
            for model, rows in mappings:
                existing = {
                    ((x.course_id, x.learner_id) if model is Enrolment else x.id): x.payload
                    for x in session.scalars(select(model))
                }
                new = []
                for row in rows:
                    key = (row["course_id"], row["learner_id"]) if model is Enrolment else row["id"]
                    if key in existing:
                        if digest(existing[key]) != digest(row["payload"]):
                            raise Conflict(f"Immutable {model.__tablename__} ID differs: {key}")
                    else:
                        existing[key] = row["payload"]
                        new.append(row)
                for offset in range(0, len(new), 500):
                    session.execute(insert(model), new[offset : offset + 500])
                counts[model.__tablename__] = len(new)
            for course in dataset["courses"]:
                if session.get(Policy, (course["presentation_id"], 1)) is None:
                    policy = CoursePolicy.model_validate(course.get("policy", {}))
                    session.add(
                        Policy(
                            course_id=course["presentation_id"],
                            version=1,
                            payload={**payload(policy), "version": 1},
                            actor="system:import",
                            created_at=now(),
                        )
                    )
            register_heads(session, [Snapshot(**row) for row in mappings[-1][1]])
        return counts

    def courses(self, allowed: list[str] | tuple[str, ...] | None = None) -> list[dict]:
        with Session(self.engine) as session:
            query = select(Course)
            if allowed is not None:
                query = query.where(Course.id.in_(allowed))
            result = []
            for course in session.scalars(query.order_by(Course.id)):
                weeks = session.scalars(
                    select(Snapshot.week)
                    .where(Snapshot.course_id == course.id)
                    .distinct()
                    .order_by(Snapshot.week)
                ).all()
                result.append({**course.payload, "checkpoints": weeks})
            return result

    def get_policy(self, presentation_id: str, version: int | None = None) -> CoursePolicy:
        with Session(self.engine) as session:
            query = select(Policy).where(Policy.course_id == presentation_id)
            if version is not None:
                query = query.where(Policy.version == version)
            row = session.scalar(query.order_by(Policy.version.desc()).limit(1))
            if row is None:
                raise LookupError("Course policy not found")
            return CoursePolicy.model_validate(row.payload)

    def set_policy(self, presentation_id: str, policy: CoursePolicy, actor: str):
        with Session(self.engine) as session, session.begin():
            current = session.scalar(
                select(func.max(Policy.version)).where(Policy.course_id == presentation_id)
            )
            if current is None:
                raise LookupError("Course not found")
            if current != policy.version:
                raise Conflict("Policy changed in another session. Reload settings first.")
            revised = policy.model_copy(update={"version": current + 1})
            session.add(
                Policy(
                    course_id=presentation_id,
                    version=revised.version,
                    payload=payload(revised),
                    actor=actor,
                    created_at=now(),
                )
            )
            session.execute(
                update(AnalysisJob)
                .where(
                    AnalysisJob.state_id.in_(
                        select(Snapshot.id).where(Snapshot.course_id == presentation_id)
                    ),
                    AnalysisJob.policy_version != revised.version,
                    AnalysisJob.status == "queued",
                )
                .values(
                    status="failed",
                    error_code="ANALYSIS_SUPERSEDED",
                    updated_at=now(),
                    lease_until=None,
                )
            )
        return revised

    def get_snapshot(self, state_id: str) -> LearnerSnapshot:
        with Session(self.engine) as session:
            state = session.get(Snapshot, state_id)
            if state is None:
                raise LookupError("Snapshot not found")
            return LearnerSnapshot.model_validate(state.payload)

    def enqueue(
        self,
        course_id: str,
        week: int,
        learner_ids: list[str] | None = None,
        model_kind: str = "llm",
        runtime_fingerprint: str = "",
        expected_model_digest: str | None = None,
    ) -> list[str]:
        policy = self.get_policy(course_id)
        with Session(self.engine) as session, session.begin():
            query = (
                select(Snapshot)
                .join(SnapshotHead, SnapshotHead.state_id == Snapshot.id)
                .where(Snapshot.course_id == course_id, Snapshot.week == week)
            )
            if learner_ids is not None:
                query = query.where(Snapshot.learner_id.in_(learner_ids))
            states = session.scalars(query).all()
            if not states:
                raise LookupError("No snapshots at this checkpoint")
            jobs = []
            for state in states:
                key = digest(
                    [
                        state.input_hash,
                        payload(policy),
                        model_kind,
                        runtime_fingerprint,
                        expected_model_digest,
                        "analysis-v2.1",
                    ]
                )
                row = session.get(AnalysisJob, key)
                if row is None:
                    session.add(
                        AnalysisJob(
                            id=key,
                            state_id=state.id,
                            policy_version=policy.version,
                            model_kind=model_kind,
                            expected_model_digest=expected_model_digest,
                            status="queued",
                            attempts=0,
                            created_at=now(),
                            updated_at=now(),
                        )
                    )
                elif row.status == "failed":
                    if row.attempts >= MAX_ATTEMPTS:
                        continue
                    row.status, row.lease_until, row.updated_at = "queued", None, now()
                jobs.append(key)
            return jobs

    def claim_job(
        self, worker_id: str, lease_seconds: int = 300, model_kind: str | None = None
    ) -> dict | None:
        moment = now()
        with Session(self.engine) as session, session.begin():
            exhausted = session.scalars(
                select(AnalysisJob).where(
                    AnalysisJob.status == "running",
                    AnalysisJob.lease_until < moment,
                    AnalysisJob.attempts >= MAX_ATTEMPTS,
                )
            ).all()
            for old_job in exhausted:
                old_job.status = "failed"
                old_job.error_code = "ANALYSIS_WORKER_INTERRUPTED"
                old_job.lease_until = None
                old_job.updated_at = moment
                session.add(
                    AnalysisAttempt(
                        id=uuid.uuid4().hex,
                        job_id=old_job.id,
                        attempt=old_job.attempts,
                        error_code=old_job.error_code,
                        outcome="lease_expired",
                        created_at=moment,
                    )
                )
            eligible = or_(
                and_(
                    AnalysisJob.status == "queued",
                    or_(AnalysisJob.lease_until.is_(None), AnalysisJob.lease_until <= moment),
                ),
                and_(AnalysisJob.status == "running", AnalysisJob.lease_until < moment),
            )
            if model_kind:
                eligible = and_(eligible, AnalysisJob.model_kind == model_kind)
            controls = {
                row.course_id: row.payload for row in session.scalars(select(CourseAnalysisControl))
            }
            paused = [
                course for course, control in controls.items() if control.get("status") == "paused"
            ]
            course_filter = or_(AnalysisJob.model_kind != "llm", Snapshot.course_id.not_in(paused))
            candidates = session.execute(
                select(Snapshot.course_id, func.min(AnalysisJob.created_at))
                .join(AnalysisJob, AnalysisJob.state_id == Snapshot.id)
                .where(eligible, course_filter)
                .group_by(Snapshot.course_id)
            ).all()
            if not candidates:
                return None
            # Least recently served course first; within a course prioritize its newest week.
            course_id = min(
                candidates,
                key=lambda row: (
                    controls.get(row[0], {}).get("last_claimed_at") or "",
                    row[1].isoformat(),
                    row[0],
                ),
            )[0]
            job = session.scalar(
                select(AnalysisJob)
                .join(Snapshot, AnalysisJob.state_id == Snapshot.id)
                .where(eligible, course_filter, Snapshot.course_id == course_id)
                .order_by(Snapshot.week.desc(), AnalysisJob.created_at)
                .limit(1)
            )
            if job is None:
                return None
            changed = session.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == job.id, eligible)
                .values(
                    status="running",
                    worker_id=worker_id,
                    lease_until=moment + timedelta(seconds=lease_seconds),
                    attempts=AnalysisJob.attempts + 1,
                    updated_at=moment,
                )
                .execution_options(synchronize_session=False)
            )
            if not changed.rowcount:
                return None
            state = session.get(Snapshot, job.state_id)
            if job.model_kind == "llm":
                save_control(
                    session,
                    course_id,
                    last_claimed_at=moment.isoformat(),
                    resume_acknowledged_at=moment.isoformat(),
                )
            return {
                "id": job.id,
                "state_id": job.state_id,
                "policy_version": job.policy_version,
                "model_kind": job.model_kind,
                "status": "running",
                "worker_id": worker_id,
                "expected_model_digest": job.expected_model_digest,
                "attempts": job.attempts + 1,
                "course_id": course_id,
                "week": state.week,
                "lease_until": (moment + timedelta(seconds=lease_seconds)).isoformat(),
            }

    def complete_job(self, job_id: str, result: dict, worker_id: str | None = None):
        output = ModelOutput.model_validate(result["output"])
        with Session(self.engine) as session, session.begin():
            job = session.get(AnalysisJob, job_id)
            if job is None or job.status != "running" or (worker_id and job.worker_id != worker_id):
                raise Conflict("Analysis lease is no longer owned by this worker")
            conditions = [
                AnalysisJob.id == job_id,
                AnalysisJob.status == "running",
                AnalysisJob.lease_until >= now(),
            ]
            if worker_id:
                conditions.append(AnalysisJob.worker_id == worker_id)
            changed = session.execute(
                update(AnalysisJob)
                .where(*conditions)
                .values(
                    status="abstained" if output.abstain else "validated",
                    updated_at=now(),
                    lease_until=None,
                    error_code=None,
                    worker_id=None,
                )
                .execution_options(synchronize_session=False)
            )
            if changed.rowcount != 1:
                raise Conflict("Analysis lease expired or changed ownership")
            plan = session.get(AnalysisPlan, job.id)
            stored = {
                **result,
                "inference_attempts": safe_attempts(result.get("inference_attempts", [])),
                "policy_version": job.policy_version,
                "state_id": job.state_id,
                "job_id": job.id,
                "model_kind": job.model_kind,
                "generated_at": now().isoformat(),
                "planned_runtime_fingerprint": plan.fingerprint if plan else None,
            }
            session.add(
                Analysis(
                    id=job.id,
                    state_id=job.state_id,
                    policy_version=job.policy_version,
                    model_kind=job.model_kind,
                    payload=stored,
                    created_at=now(),
                )
            )
            session.add(
                AnalysisAttempt(
                    id=uuid.uuid4().hex,
                    job_id=job.id,
                    attempt=job.attempts,
                    error_code=None,
                    outcome="abstained" if output.abstain else "validated",
                    created_at=now(),
                )
            )
            persist_traces(session, job, stored["inference_attempts"])

    def fail_job(
        self,
        job_id: str,
        error_code: str,
        worker_id: str | None = None,
        *,
        retryable: bool = False,
        attempt_metadata: list | None = None,
    ):
        with Session(self.engine) as session, session.begin():
            conditions = [AnalysisJob.id == job_id, AnalysisJob.status == "running"]
            if worker_id:
                conditions.append(AnalysisJob.worker_id == worker_id)
            job = session.get(AnalysisJob, job_id)
            if job is None or job.status != "running" or (worker_id and job.worker_id != worker_id):
                return "lease_changed"
            retry = retryable and job.attempts < MAX_ATTEMPTS
            next_attempt = (
                now() + timedelta(seconds=30 * (3 ** max(0, job.attempts - 1))) if retry else None
            )
            changed = session.execute(
                update(AnalysisJob)
                .where(*conditions)
                .values(
                    status="queued" if retry else "failed",
                    error_code=error_code[:128],
                    lease_until=next_attempt,
                    worker_id=None,
                    updated_at=now(),
                )
            )
            if changed.rowcount:
                session.add(
                    AnalysisAttempt(
                        id=uuid.uuid4().hex,
                        job_id=job.id,
                        attempt=job.attempts,
                        error_code=error_code[:128],
                        outcome="retry_scheduled" if retry else "failed",
                        created_at=now(),
                    )
                )
                persist_traces(session, job, attempt_metadata)
            return "retry_scheduled" if retry else "failed"

    def job_summary(self) -> dict:
        with Session(self.engine) as session:
            return dict(
                session.execute(
                    select(AnalysisJob.status, func.count()).group_by(AnalysisJob.status)
                ).all()
            )

    @staticmethod
    def _current_result(result, policy_version):
        if result.policy_version != policy_version:
            return False
        if result.model_kind != "llm":
            return True
        from .llm import PROMPT_VERSION, RuntimeConfig

        try:
            config = RuntimeConfig.from_environment()
        except ValueError:
            return False
        data = result.payload
        if (
            data.get("prompt_version") != PROMPT_VERSION
            or data.get("model_version") != config.model
        ):
            return False
        if (
            config.expected_digest
            and data.get("inference_performed")
            and data.get("model_digest") != config.expected_digest
        ):
            return False
        planned = data.get("planned_runtime_fingerprint")
        if planned:
            return planned == digest(
                [config.model, PROMPT_VERSION, config.context_tokens, config.max_tokens]
            )
        runtime = data.get("runtime", {})
        return not data.get("inference_performed") or (
            runtime.get("context_tokens") == config.context_tokens
            and runtime.get("max_tokens") == config.max_tokens
        )

    @staticmethod
    def _comparison(a: dict | None, b: dict | None) -> bool:
        if not a or not b or a["output"]["abstain"] or b["output"]["abstain"]:
            return False
        return all(
            a.get(k) == b.get(k)
            for k in (
                "model_version",
                "model_digest",
                "prompt_version",
                "feature_version",
                "policy_version",
                "calibration_version",
            )
        )

    def workspace(
        self,
        course_id: str,
        week: int,
        query: str = "",
        risk: str = "",
        status: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        policy = self.get_policy(course_id)
        with Session(self.engine) as session:
            course = session.get(Course, course_id)
            if course is None:
                raise LookupError("Course not found")
            enrolments = session.scalars(
                select(Enrolment).where(Enrolment.course_id == course_id)
            ).all()
            previous_checkpoint = session.scalar(
                select(func.max(Snapshot.week)).where(
                    Snapshot.course_id == course_id, Snapshot.week < week
                )
            )
            selected_weeks = [week] + (
                [previous_checkpoint] if previous_checkpoint is not None else []
            )
            states = session.scalars(
                select(Snapshot)
                .join(SnapshotHead, SnapshotHead.state_id == Snapshot.id)
                .where(Snapshot.course_id == course_id, Snapshot.week.in_(selected_weeks))
            ).all()
            states_by_learner = {}
            for state in states:
                states_by_learner.setdefault(state.learner_id, {})[state.week] = state
            # Join via course to avoid SQLite bind-variable limits for large cohorts.
            analyses = session.scalars(
                select(Analysis)
                .join(Snapshot, Analysis.state_id == Snapshot.id)
                .where(Snapshot.course_id == course_id, Snapshot.week.in_(selected_weeks))
                .order_by((Analysis.policy_version == policy.version), Analysis.created_at)
            ).all()
            by_state = {}
            for analysis in analyses:
                existing = by_state.get(analysis.state_id)
                if existing is None or analysis.model_kind == "llm" or existing.model_kind != "llm":
                    by_state[analysis.state_id] = analysis
            jobs = session.scalars(
                select(AnalysisJob)
                .join(Snapshot, AnalysisJob.state_id == Snapshot.id)
                .where(Snapshot.course_id == course_id, Snapshot.week == week)
                .order_by((AnalysisJob.policy_version == policy.version), AnalysisJob.updated_at)
            ).all()
            job_by_state = {}
            for job in jobs:
                if (
                    job.state_id not in job_by_state
                    or job.model_kind == "llm"
                    or job_by_state[job.state_id].model_kind != "llm"
                ):
                    job_by_state[job.state_id] = job
            cases = {
                x.learner_id: x
                for x in session.scalars(
                    select(SupportCase).where(SupportCase.course_id == course_id)
                )
            }
            latest_case_events = {}
            for case_event in session.scalars(
                select(CaseEvent)
                .join(SupportCase, CaseEvent.case_id == SupportCase.id)
                .where(SupportCase.course_id == course_id, CaseEvent.occurred_day <= week * 7 - 1)
                .order_by(CaseEvent.created_at)
            ):
                latest_case_events[case_event.case_id] = case_event
            items = []
            for enrol in enrolments:
                ep = enrol.payload
                cutoff = week * 7 - 1
                if ep.get("registration_day") is not None and ep["registration_day"] > cutoff:
                    continue
                if ep.get("unregistration_day") is not None and ep["unregistration_day"] <= cutoff:
                    continue
                ls = states_by_learner.get(enrol.learner_id, {})
                state = ls.get(week)
                result = by_state.get(state.id) if state else None
                a = result.payload if result else None
                previous_weeks = sorted(w for w in ls if w < week)
                prior = by_state.get(ls[previous_weeks[-1]].id) if previous_weeks else None
                b = prior.payload if prior else None
                compatible = self._comparison(a, b) and result.policy_version == policy.version
                out = a["output"] if a else {}
                job = job_by_state.get(state.id) if state else None
                analysis_status = job.status if job else "not_run"
                if result and not job:
                    analysis_status = "abstained" if out.get("abstain") else "validated"
                if (
                    result
                    and not self._current_result(result, policy.version)
                    and analysis_status not in {"queued", "running", "failed"}
                ):
                    analysis_status = "outdated"
                usable = bool(
                    a and analysis_status == "validated" and state and state.payload["is_fresh"]
                )
                case = cases.get(enrol.learner_id)
                latest_event = latest_case_events.get(case.id) if case else None
                case_status = latest_event.payload["status"] if latest_event else None
                followup = latest_event.payload.get("follow_up_day") if latest_event else None
                items.append(
                    {
                        "learner_id": enrol.learner_id,
                        "display_name": ep.get("display_name", enrol.learner_id),
                        "checkpoint_week": week,
                        "state_id": state.id if state else None,
                        "risk_score": out.get("risk_score") if usable else None,
                        "risk_band": out.get("risk_band") if usable else None,
                        "previous_score": b["output"].get("risk_score") if compatible else None,
                        "change": out["risk_score"] - b["output"]["risk_score"]
                        if compatible and usable
                        else None,
                        "previous_week": previous_weeks[-1] if previous_weeks else None,
                        "analysis_status": analysis_status,
                        "model_version": a.get("model_version") if a else None,
                        "case_status": case_status,
                        "case_version": case.version if case else 0,
                        "follow_up_day": followup,
                        "is_fresh": state.payload["is_fresh"] if state else False,
                        "comparable": bool(compatible and usable),
                        "reason": out.get("abstention_reason")
                        or (job.error_code if job and job.status == "failed" else ""),
                        "needs_review": case_status == "new"
                        or (
                            followup is not None
                            and followup <= cutoff
                            and case_status in {"ongoing", "reviewed"}
                        )
                        or (
                            usable
                            and out.get("risk_band") == "high"
                            and case_status not in {"reviewed", "ongoing", "resolved", "dismissed"}
                        ),
                    }
                )
            distribution = Counter(x["risk_band"] or "unavailable" for x in items)
            movement = Counter(
                "not_comparable"
                if x["change"] is None
                else "increased"
                if x["change"] > 0.005
                else "decreased"
                if x["change"] < -0.005
                else "stable"
                for x in items
            )
            summary = {
                "enrolled": len(items),
                "needs_review": sum(x["needs_review"] for x in items),
                "high_attention": sum(x["risk_band"] == "high" for x in items),
                "insufficient_data": sum(x["analysis_status"] == "abstained" for x in items),
                "ongoing": sum(x["case_status"] == "ongoing" for x in items),
                "not_run": sum(x["analysis_status"] in {"not_run", "outdated"} for x in items),
                "queued": sum(x["analysis_status"] in {"queued", "running"} for x in items),
                "failed": sum(x["analysis_status"] == "failed" for x in items),
            }
            filtered = [
                x
                for x in items
                if (
                    not query
                    or query.lower() in (x["learner_id"] + " " + x["display_name"]).lower()
                )
                and (
                    not risk
                    or x["risk_band"] == risk
                    or (risk == "unavailable" and x["risk_band"] is None)
                )
                and (not status or x["case_status"] == status or x["analysis_status"] == status)
            ]
            filtered.sort(
                key=lambda x: (not x["needs_review"], -(x["risk_score"] or 0), x["learner_id"])
            )
            return {
                "course": course.payload,
                "policy": payload(policy),
                "summary": summary,
                "model_counts": dict(Counter(x["model_version"] or "not_run" for x in items)),
                "distribution": {
                    k: distribution[k] for k in ("high", "medium", "low", "unavailable")
                },
                "movement": {
                    k: movement[k] for k in ("increased", "stable", "decreased", "not_comparable")
                },
                "items": filtered[offset : offset + limit],
                "total": len(filtered),
                "week": week,
            }

    def learner(self, course_id: str, learner_id: str, week: int) -> dict:
        current_policy = self.get_policy(course_id)
        with Session(self.engine) as session:
            enrol = session.get(Enrolment, (course_id, learner_id))
            course = session.get(Course, course_id)
            if enrol is None or course is None:
                raise LookupError("Learner not found in this course")
            states = session.scalars(
                select(Snapshot)
                .join(SnapshotHead, SnapshotHead.state_id == Snapshot.id)
                .where(
                    Snapshot.course_id == course_id,
                    Snapshot.learner_id == learner_id,
                    Snapshot.week <= week,
                )
                .order_by(Snapshot.week)
            ).all()
            analyses = session.scalars(
                select(Analysis)
                .join(Snapshot, Analysis.state_id == Snapshot.id)
                .where(
                    Snapshot.course_id == course_id,
                    Snapshot.learner_id == learner_id,
                    Snapshot.week <= week,
                )
                .order_by((Analysis.policy_version == current_policy.version), Analysis.created_at)
            ).all()
            by_state = {}
            for a in analyses:
                if (
                    a.state_id not in by_state
                    or a.model_kind == "llm"
                    or by_state[a.state_id].model_kind != "llm"
                ):
                    by_state[a.state_id] = a
            current = next((s for s in reversed(states) if s.week == week), None)
            current_a = by_state.get(current.id) if current else None
            baseline_a = next(
                (
                    a
                    for a in reversed(analyses)
                    if current and a.state_id == current.id and a.model_kind == "baseline"
                ),
                None,
            )
            past = [s for s in states if s.week < week]
            prev_a = by_state.get(past[-1].id) if past else None
            history = [
                {
                    "checkpoint_week": s.week,
                    "risk_score": by_state[s.id].payload["output"]["risk_score"],
                    "risk_band": by_state[s.id].payload["output"]["risk_band"],
                    "model_version": by_state[s.id].payload["model_version"],
                    "policy_version": by_state[s.id].policy_version,
                    "model_digest": by_state[s.id].payload.get("model_digest"),
                    "prompt_version": by_state[s.id].payload.get("prompt_version"),
                    "feature_version": by_state[s.id].payload.get("feature_version"),
                    "calibration_version": by_state[s.id].payload.get("calibration_version"),
                    "features": s.payload["features"],
                }
                for s in states
                if s.id in by_state
            ]
            events = session.scalars(
                select(Event)
                .where(
                    Event.course_id == course_id,
                    Event.learner_id == learner_id,
                    Event.course_day <= week * 7 - 1,
                    Event.available_day <= week * 7 - 1,
                )
                .order_by(Event.course_day)
            ).all()
            latest_job = (
                session.scalar(
                    select(AnalysisJob)
                    .where(AnalysisJob.state_id == current.id)
                    .order_by(
                        (AnalysisJob.model_kind == "llm").desc(),
                        (AnalysisJob.policy_version == current_policy.version).desc(),
                        AnalysisJob.updated_at.desc(),
                    )
                    .limit(1)
                )
                if current
                else None
            )
            analysis_status = latest_job.status if latest_job else "not_run"
            if (
                current_a
                and not self._current_result(current_a, current_policy.version)
                and analysis_status not in {"queued", "running", "failed"}
            ):
                analysis_status = "outdated"
            return {
                "learner_id": learner_id,
                "display_name": enrol.payload.get("display_name", learner_id),
                "analysis_status": analysis_status,
                "job_error": latest_job.error_code if latest_job else None,
                "job_error_detail": describe_failure(latest_job.error_code)
                if latest_job and latest_job.error_code
                else None,
                "comparable": self._comparison(
                    current_a.payload if current_a else None, prev_a.payload if prev_a else None
                )
                and analysis_status == "validated"
                and bool(current and current.payload["is_fresh"]),
                "previous_week": past[-1].week if past else None,
                "current_policy_version": current_policy.version,
                "snapshot": current.payload if current else None,
                "analysis": current_a.payload if current_a else None,
                "baseline_analysis": baseline_a.payload if baseline_a else None,
                "previous_analysis": prev_a.payload if prev_a else None,
                "history": history,
                "snapshot_history": [
                    {"checkpoint_week": s.week, "features": s.payload["features"]} for s in states
                ],
                "case": self.get_case(course_id, learner_id, week * 7 - 1),
                "resources": [
                    r
                    for r in course.payload.get("resources", [])
                    if r.get("available_day", 0) <= week * 7 - 1
                ],
                "events": [e.payload for e in events],
            }

    def get_case(self, course_id: str, learner_id: str, cutoff: int | None = None):
        with Session(self.engine) as session:
            case = session.scalar(
                select(SupportCase).where(
                    SupportCase.course_id == course_id, SupportCase.learner_id == learner_id
                )
            )
            if case is None:
                return None
            query = select(CaseEvent).where(CaseEvent.case_id == case.id)
            if cutoff is not None:
                query = query.where(CaseEvent.occurred_day <= cutoff)
            events = session.scalars(query.order_by(CaseEvent.created_at)).all()
            return {
                "id": case.id,
                "status": events[-1].payload["status"] if events else "not_started",
                "version": case.version,
                "follow_up_day": events[-1].payload.get("follow_up_day") if events else None,
                "events": [
                    {
                        **e.payload,
                        "id": e.id,
                        "actor": e.actor,
                        "recorded_at": e.created_at.isoformat(),
                    }
                    for e in events
                ],
            }

    def update_case(
        self, course_id: str, learner_id: str, change: CaseUpdate, actor: str, request_key: str
    ):
        if change.occurred_day > change.checkpoint_week * 7 - 1:
            raise ValueError(
                "Action date cannot be after the selected checkpoint. "
                "Use a follow-up date for planned future work."
            )
        if change.follow_up_day is not None and change.follow_up_day < change.occurred_day:
            raise ValueError("Follow-up cannot precede the recorded action.")
        fingerprint = digest([course_id, learner_id, payload(change)])
        try:
            with Session(self.engine) as session, session.begin():
                repeated = session.scalar(
                    select(CaseEvent).where(
                        CaseEvent.actor == actor, CaseEvent.request_key == request_key
                    )
                )
                if repeated:
                    if repeated.request_hash != fingerprint:
                        raise Conflict(
                            "This request key was already used for a different decision."
                        )
                    return self.get_case(course_id, learner_id)
                course = session.get(Course, course_id)
                if course is None or session.get(Enrolment, (course_id, learner_id)) is None:
                    raise LookupError("Learner not found in this course")
                resources = {
                    r["resource_id"]
                    for r in course.payload.get("resources", [])
                    if r.get("available_day", 0) <= change.occurred_day
                }
                if not set(change.resource_ids).issubset(resources):
                    raise ValueError("Select approved resources available at the action date.")
                case_id = digest([course_id, learner_id])
                case = session.get(SupportCase, case_id)
                if case is None:
                    if change.expected_version != 0:
                        raise Conflict("Case version changed. Reload the learner.")
                    case = SupportCase(
                        id=case_id,
                        course_id=course_id,
                        learner_id=learner_id,
                        status=change.status,
                        version=1,
                        follow_up_day=change.follow_up_day,
                    )
                    session.add(case)
                    session.flush()
                else:
                    updated = session.execute(
                        update(SupportCase)
                        .where(
                            SupportCase.id == case_id,
                            SupportCase.version == change.expected_version,
                        )
                        .values(
                            version=change.expected_version + 1,
                            status=change.status,
                            follow_up_day=change.follow_up_day,
                        )
                    )
                    if not updated.rowcount:
                        raise Conflict(
                            "Another instructor changed this case. Reload before saving."
                        )
                state = session.scalar(
                    select(Snapshot).where(
                        Snapshot.course_id == course_id,
                        Snapshot.learner_id == learner_id,
                        Snapshot.week == change.checkpoint_week,
                    )
                )
                event_payload = {
                    **payload(change),
                    "state_id": state.id if state else None,
                    "interpretation": (
                        "Recorded instructor action; subsequent change is observational, "
                        "not proof of causation."
                    ),
                }
                session.add(
                    CaseEvent(
                        id=uuid.uuid4().hex,
                        case_id=case_id,
                        actor=actor,
                        request_key=request_key,
                        request_hash=fingerprint,
                        occurred_day=change.occurred_day,
                        payload=event_payload,
                        created_at=now(),
                    )
                )
        except IntegrityError as error:
            raise Conflict(
                "Concurrent change detected. Reload and retry with the same request key."
            ) from error
        return self.get_case(course_id, learner_id)
