"""Separate instructor-owned validation pauses from operator-owned service health."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .errors import describe_failure
from .models import AnalysisJob, Course, CourseAnalysisControl, RuntimeState, Snapshot


def utc_now():
    return datetime.now(UTC)


def defaults():
    return {
        "status": "active",
        "failure_streak": 0,
        "last_error_code": None,
        "pause_scope": "course",
        "resume_requested_at": None,
        "resume_acknowledged_at": None,
        "last_claimed_at": None,
    }


def save_control(session, course_id, **values):
    row = session.get(CourseAnalysisControl, course_id)
    if row is None:
        row = CourseAnalysisControl(
            course_id=course_id, payload={**defaults(), **values}, updated_at=utc_now()
        )
        session.add(row)
    else:
        row.payload = {**row.payload, **values}
        row.updated_at = utc_now()
    return row


class ControlsMixin:
    def get_course_control(self, course_id):
        with Session(self.engine) as session:
            if session.get(Course, course_id) is None:
                raise LookupError("Course not found")
            row = session.get(CourseAnalysisControl, course_id)
            return {
                **defaults(),
                **(row.payload if row else {}),
                "updated_at": row.updated_at.isoformat() if row else None,
            }

    def record_course_outcome(self, course_id, error_code=None):
        """Count consecutive final validation failures within this course, not across courses."""
        with Session(self.engine) as session, session.begin():
            row = session.get(CourseAnalysisControl, course_id)
            prior = row.payload if row else defaults()
            streak = int(prior.get("failure_streak", 0)) + 1 if error_code else 0
            values = {
                "failure_streak": streak,
                "last_error_code": error_code,
                "last_outcome_at": utc_now().isoformat(),
            }
            if error_code and streak >= 3:
                values.update(status="paused", paused_at=utc_now().isoformat())
            # An in-flight success never clears a pause requested after the claim.
            save_control(session, course_id, **values)

    def resume_analysis(self, course_id, actor="operator"):
        self.get_course_control(course_id)  # Refuse unknown courses before writing.
        with Session(self.engine) as session, session.begin():
            save_control(
                session,
                course_id,
                status="active",
                failure_streak=0,
                last_error_code=None,
                resume_requested_at=utc_now().isoformat(),
                resume_actor=actor,
            )
        # A user request is not a worker heartbeat or acknowledgement.
        return self.get_course_control(course_id)

    def migrate_legacy_validation_pause(self):
        """Move an old global output-validation pause to its responsible course, once."""
        with Session(self.engine) as session, session.begin():
            runtime = session.get(RuntimeState, "worker")
            if runtime is None:
                return False
            prior = runtime.payload
            if prior.get("status") != "paused" or prior.get("pause_scope") is not None:
                return False
            failure = describe_failure(prior.get("last_error_code"))
            if failure["category"] not in {"grounding", "output"} or failure["service_blocking"]:
                runtime.payload = {**prior, "pause_scope": "service"}
                return False
            failed = session.execute(
                select(AnalysisJob, Snapshot.course_id)
                .join(Snapshot)
                .where(
                    AnalysisJob.model_kind == "llm",
                    AnalysisJob.status == "failed",
                    AnalysisJob.error_code == failure["code"],
                )
                .order_by(AnalysisJob.updated_at.desc())
                .limit(1)
            ).first()
            if failed is None:
                runtime.payload = {**prior, "pause_scope": "legacy_validation"}
                return False  # Don't silently lift an unattributable protective pause.
            _job, course_id = failed
            save_control(
                session,
                course_id,
                status="paused",
                failure_streak=max(3, int(prior.get("failure_streak", 3))),
                last_error_code=failure["code"],
                migrated_from_global=True,
            )
            runtime.payload = {
                **prior,
                "status": "starting",
                "pause_scope": None,
                "last_error_code": None,
                "failure_streak": 0,
                "pause_until": None,
                "legacy_pause_migrated_at": utc_now().isoformat(),
            }
            runtime.updated_at = utc_now()
            return True

    def resume_service(self):
        """Operator-only action; never exposed through an instructor course route."""
        with Session(self.engine) as session, session.begin():
            row = session.get(RuntimeState, "worker")
            if row is None:
                raise LookupError("Worker has not started; use the deployment startup procedure.")
            row.payload = {
                **row.payload,
                "status": "resume_requested",
                "pause_until": None,
                "pause_scope": None,
                "last_error_code": None,
                "failure_streak": 0,
                "worker_heartbeat_at": row.payload.get("worker_heartbeat_at")
                or row.updated_at.isoformat(),
                "operator_resume_requested_at": utc_now().isoformat(),
            }
            row.updated_at = utc_now()
        return self.get_runtime()

    def public_worker_status(self, course_id):
        runtime = self.get_runtime()
        keys = (
            "status",
            "heartbeat_at",
            "heartbeat_age_seconds",
            "pause_until",
            "last_error_code",
            "pause_scope",
            "active_deadline_at",
        )
        result = {key: runtime.get(key) for key in keys}
        active = (
            runtime.get("active_course_id")
            if runtime.get("status") != "heartbeat_stale"
            else None
        )
        result["is_processing_this_course"] = bool(active and active == course_id)
        result["processing_another_course"] = bool(active and active != course_id)
        if active == course_id:
            result["active_week"] = runtime.get("active_week")
        return result
