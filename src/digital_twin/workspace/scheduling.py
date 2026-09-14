"""Course-scoped catch-up and bounded automatic discovery; no inference in HTTP requests."""

from collections import Counter, defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .contracts import digest
from .errors import describe_failure
from .models import (
    Analysis,
    AnalysisJob,
    AnalysisPlan,
    Automation,
    Course,
    RuntimeState,
    Snapshot,
    SnapshotHead,
)

MAX_ATTEMPTS = 3
AUTO_BACKLOG_LIMIT = 200


def moment():
    return datetime.now(UTC)


def aware(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def semantic_hash(payload):
    return digest({k: v for k, v in payload.items() if k not in {"state_id", "built_at"}})


def runtime_spec(client=None):
    from .llm import PROMPT_VERSION, OllamaClient

    runtime = client or OllamaClient()
    ready = runtime.readiness()
    config = runtime.config
    expected = config.expected_digest or ready.get("digest")
    return {
        "model": config.model,
        "digest": expected,
        "prompt_version": PROMPT_VERSION,
        "fingerprint": digest(
            [config.model, PROMPT_VERSION, config.context_tokens, config.max_tokens]
        ),
        "ready": ready,
    }


def register_heads(session, states):
    heads = {(h.course_id, h.learner_id, h.week): h for h in session.scalars(select(SnapshotHead))}
    for state in sorted(states, key=lambda s: (aware(s.payload["built_at"]), s.id)):
        key = (state.course_id, state.learner_id, state.week)
        head = heads.get(key)
        if head is None:
            head = SnapshotHead(course_id=key[0], learner_id=key[1], week=key[2], state_id=state.id)
            session.add(head)
            heads[key] = head
        elif head.state_id != state.id:
            previous = session.get(Snapshot, head.state_id)
            if semantic_hash(previous.payload) == semantic_hash(state.payload):
                continue  # Rebuilding an unchanged snapshot must not trigger another model call.
            earlier, newer = aware(previous.payload["built_at"]), aware(state.payload["built_at"])
            if newer == earlier:
                raise ValueError("Different weekly revisions need distinct build timestamps.")
            if newer > earlier:
                head.state_id = state.id
                session.execute(
                    update(AnalysisJob)
                    .where(AnalysisJob.state_id == previous.id, AnalysisJob.status == "queued")
                    .values(
                        status="failed",
                        error_code="ANALYSIS_SUPERSEDED",
                        lease_until=None,
                        updated_at=moment(),
                    )
                )


def plan_matches(plan, result, spec):
    if plan is not None:
        return plan.fingerprint == spec["fingerprint"]
    if result is None:
        return False  # Legacy failures did not record their planned prompt/runtime.
    data = result.payload
    runtime = data.get("runtime", {})
    old_fingerprint = digest(
        [
            data.get("model_version"),
            data.get("prompt_version"),
            runtime.get("context_tokens"),
            runtime.get("max_tokens"),
        ]
    )
    return old_fingerprint == spec["fingerprint"]


class SchedulingMixin:
    def ensure_heads(self):
        """Backfill pointers when upgrading the old pilot; called outside request inference."""
        with Session(self.engine) as session, session.begin():
            register_heads(session, session.scalars(select(Snapshot)).all())

    def get_automation(self, course_id):
        with Session(self.engine) as session:
            if session.get(Course, course_id) is None:
                raise LookupError("Course not found")
            row = session.get(Automation, course_id)
            return (
                {"enabled": row.enabled, "version": row.version}
                if row
                else {"enabled": True, "version": 1}
            )

    def set_automation(self, course_id, enabled, version, actor):
        from .store import Conflict

        with Session(self.engine) as session, session.begin():
            if session.get(Course, course_id) is None:
                raise LookupError("Course not found")
            row = session.get(Automation, course_id)
            if row is None:
                if version != 1:
                    raise Conflict("Automation settings changed; refresh first.")
                session.add(
                    Automation(
                        course_id=course_id,
                        enabled=enabled,
                        version=2,
                        actor=actor,
                        updated_at=moment(),
                    )
                )
            else:
                changed = session.execute(
                    update(Automation)
                    .where(Automation.course_id == course_id, Automation.version == version)
                    .values(enabled=enabled, version=version + 1, actor=actor, updated_at=moment())
                )
                if changed.rowcount != 1:
                    raise Conflict("Automation settings changed; refresh first.")
        return {"enabled": enabled, "version": version + 1}

    def get_runtime(self):
        with Session(self.engine) as session:
            row = session.get(RuntimeState, "worker")
            if row is None:
                return {"status": "not_started", "heartbeat_at": None}
            result = dict(row.payload)
            result["heartbeat_at"] = aware(row.updated_at).isoformat()
            # A bounded call can take 300s; don't label an active inference as a dead worker.
            if (moment() - aware(row.updated_at)).total_seconds() > 360:
                result["last_reported_status"] = result.get("status")
                result["status"] = "heartbeat_stale"
            return result

    def set_runtime(self, **values):
        with Session(self.engine) as session, session.begin():
            row = session.get(RuntimeState, "worker")
            if row is None:
                session.add(RuntimeState(id="worker", payload=values, updated_at=moment()))
            else:
                row.payload = {**row.payload, **values}
                row.updated_at = moment()

    def resume_analysis(self):
        self.set_runtime(
            status="resuming", pause_until=None, last_error_code=None, failure_streak=0
        )
        return self.get_runtime()

    def job_matches_runtime(self, job_id, spec):
        with Session(self.engine) as session:
            return plan_matches(session.get(AnalysisPlan, job_id), None, spec)

    def _analysis_rows(self, session, course_id, spec, week=None, learner_ids=None):
        policy = self.get_policy(course_id)
        query = (
            select(Snapshot)
            .join(SnapshotHead, SnapshotHead.state_id == Snapshot.id)
            .where(Snapshot.course_id == course_id)
            .order_by(Snapshot.week.desc(), Snapshot.learner_id)
        )
        if week is not None:
            query = query.where(Snapshot.week == week)
        if learner_ids is not None:
            query = query.where(Snapshot.learner_id.in_(learner_ids))
        states = session.scalars(query).all()
        jobs = session.scalars(
            select(AnalysisJob)
            .join(Snapshot)
            .where(
                Snapshot.course_id == course_id,
                AnalysisJob.model_kind == "llm",
                AnalysisJob.policy_version == policy.version,
            )
            .order_by(AnalysisJob.updated_at, AnalysisJob.id)
        ).all()
        results = {
            a.id: a
            for a in session.scalars(
                select(Analysis)
                .join(Snapshot)
                .where(Snapshot.course_id == course_id, Analysis.model_kind == "llm")
            )
        }
        plans = {
            p.job_id: p
            for p in session.scalars(
                select(AnalysisPlan)
                .join(AnalysisJob)
                .join(Snapshot)
                .where(Snapshot.course_id == course_id)
            )
        }
        by_state = {}
        for job in jobs:
            if spec.get("digest") and job.expected_model_digest not in {None, spec["digest"]}:
                continue
            if not plan_matches(plans.get(job.id), results.get(job.id), spec):
                continue
            by_state[job.state_id] = job
        baseline_states = set(
            session.scalars(
                select(Analysis.state_id)
                .join(Snapshot)
                .where(Snapshot.course_id == course_id, Analysis.model_kind == "baseline")
            )
        )
        previous_work = session.execute(
            select(Snapshot.learner_id, Snapshot.week, Snapshot.id)
            .join(AnalysisJob, AnalysisJob.state_id == Snapshot.id)
            .where(Snapshot.course_id == course_id, AnalysisJob.model_kind == "llm")
        ).all()
        worked_slots = {(learner, w) for learner, w, _state in previous_work}
        worked_ids = {state_id for _learner, _week, state_id in previous_work}
        newest_worked_week = max((w for _learner, w, _id in previous_work), default=None)
        rows = []
        for state in states:
            job = by_state.get(state.id)
            status = job.status if job else "unassessed"
            result = results.get(job.id) if job else None
            if status in {"validated", "abstained"}:
                data = result.payload if result else {}
                if (
                    data.get("prompt_version") != spec["prompt_version"]
                    or data.get("model_version") != spec["model"]
                    or (
                        spec.get("digest")
                        and data.get("inference_performed")
                        and data.get("model_digest") != spec["digest"]
                    )
                ):
                    status = "unassessed"
            if status == "queued" and job.lease_until and aware(job.lease_until) > moment():
                status = "retry_scheduled"
            rows.append(
                {
                    "state": state,
                    "job": job,
                    "status": status,
                    "baseline_only": state.id in baseline_states
                    and status not in {"validated", "abstained"},
                    "priority": state.id not in worked_ids
                    and (
                        (state.learner_id, state.week) in worked_slots
                        or (newest_worked_week is not None and state.week > newest_worked_week)
                    ),
                }
            )
        return policy, rows

    def queue_analysis(
        self,
        course_id,
        spec,
        *,
        week=None,
        learner_ids=None,
        mode="unassessed",
        limit=None,
        priority_only=False,
    ):
        """Queue current learner-week revisions once. Failed jobs need an explicit retry."""
        if mode not in {"unassessed", "retry_failed"}:
            raise ValueError("Unknown analysis queue mode")
        counts = dict(queued=0, already_queued=0, already_assessed=0, failed_skipped=0, exhausted=0)
        with Session(self.engine) as session, session.begin():
            policy, rows = self._analysis_rows(session, course_id, spec, week, learner_ids)
            active_states = {r["state"].id for r in rows}
            current_job_ids = {r["job"].id for r in rows if r["job"] is not None}
            pending = session.scalars(
                select(AnalysisJob)
                .join(Snapshot)
                .where(
                    Snapshot.course_id == course_id,
                    AnalysisJob.model_kind == "llm",
                    AnalysisJob.status == "queued",
                )
            ).all()
            for old in pending:
                if old.state_id in active_states and old.id not in current_job_ids:
                    old.status, old.error_code = "failed", "ANALYSIS_SUPERSEDED"
                    old.lease_until, old.updated_at = None, moment()
            for row in rows:
                if priority_only and not row["priority"]:
                    continue
                state, job, status = row["state"], row["job"], row["status"]
                if status in {"queued", "running", "retry_scheduled"}:
                    counts["already_queued"] += 1
                    continue
                if status in {"validated", "abstained"}:
                    counts["already_assessed"] += 1
                    continue
                if status == "failed" and mode != "retry_failed":
                    counts["failed_skipped"] += 1
                    continue
                if mode == "retry_failed" and status != "failed":
                    continue
                if limit is not None and counts["queued"] >= limit:
                    continue
                if status == "failed":
                    if job.attempts >= MAX_ATTEMPTS:
                        counts["exhausted"] += 1
                        continue
                    job.status, job.lease_until, job.worker_id = "queued", None, None
                    job.updated_at = moment()  # retain the last failure code for diagnosis
                else:
                    key = digest(
                        [
                            state.input_hash,
                            policy.model_dump(mode="json"),
                            "llm",
                            spec["fingerprint"],
                            spec.get("digest"),
                            "planned-analysis-v1",
                        ]
                    )
                    existing = session.get(AnalysisJob, key)
                    if existing is not None:
                        counts["failed_skipped"] += 1
                        continue
                    session.add(
                        AnalysisJob(
                            id=key,
                            state_id=state.id,
                            policy_version=policy.version,
                            model_kind="llm",
                            expected_model_digest=spec.get("digest"),
                            status="queued",
                            attempts=0,
                            created_at=moment(),
                            updated_at=moment(),
                        )
                    )
                    session.flush()  # Persist FK target before its planned-runtime record.
                    session.add(
                        AnalysisPlan(
                            job_id=key, fingerprint=spec["fingerprint"], created_at=moment()
                        )
                    )
                counts["queued"] += 1
        return {**counts, "model_ready": spec["ready"]["status"] == "ready"}

    def discover_analysis(self, spec, limit=AUTO_BACKLOG_LIMIT):
        if spec["ready"]["status"] != "ready":
            return 0
        if spec.get("digest"):
            with Session(self.engine) as session, session.begin():
                session.execute(
                    update(AnalysisJob)
                    .where(
                        AnalysisJob.model_kind == "llm",
                        AnalysisJob.status == "queued",
                        AnalysisJob.expected_model_digest.is_not(None),
                        AnalysisJob.expected_model_digest != spec["digest"],
                    )
                    .values(
                        status="failed",
                        error_code="ANALYSIS_SUPERSEDED",
                        updated_at=moment(),
                        lease_until=None,
                    )
                )
        with Session(self.engine) as session:
            backlog = session.scalar(
                select(func.count())
                .select_from(AnalysisJob)
                .where(
                    AnalysisJob.model_kind == "llm", AnalysisJob.status.in_(["queued", "running"])
                )
            )
            courses = session.scalars(select(Course.id).order_by(Course.id)).all()
        remaining = max(0, limit - backlog)
        total = 0
        for course in courses:
            if self.get_automation(course)["enabled"]:
                urgent = self.queue_analysis(course, spec, limit=20, priority_only=True)["queued"]
                total += urgent
                remaining = max(0, remaining - urgent)
                if remaining:
                    queued = self.queue_analysis(course, spec, limit=min(50, remaining))["queued"]
                    total += queued
                    remaining -= queued
        return total

    def analysis_status(self, course_id, spec):
        with Session(self.engine) as session:
            _policy, rows = self._analysis_rows(session, course_id, spec)
            total, weeks, failures = Counter(), defaultdict(Counter), Counter()
            for row in rows:
                state, job, status = row["state"], row["job"], row["status"]
                for count in (total, weeks[state.week]):
                    count["total_snapshots"] += 1
                    count[status] += 1
                    count["baseline_only"] += row["baseline_only"]
                if (
                    job
                    and job.error_code
                    and status in {"failed", "retry_scheduled", "queued", "running"}
                ):
                    failures[job.error_code] += 1
            keys = (
                "total_snapshots",
                "validated",
                "abstained",
                "queued",
                "running",
                "retry_scheduled",
                "failed",
                "unassessed",
                "baseline_only",
            )
            return {
                "automation": self.get_automation(course_id),
                "model": spec["ready"],
                "worker": self.get_runtime(),
                "summary": {k: total[k] for k in keys},
                "weeks": [
                    {"week": w, **{k: counts[k] for k in keys}}
                    for w, counts in sorted(weeks.items())
                ],
                "failures": [
                    {**describe_failure(code), "count": n} for code, n in failures.most_common()
                ],
                "max_attempts": MAX_ATTEMPTS,
            }
