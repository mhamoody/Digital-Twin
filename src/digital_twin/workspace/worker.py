"""One-process durable inference worker, independently restartable from the UI."""

from __future__ import annotations

import logging
import signal
import threading
import time
import uuid
from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError

from .errors import describe_failure, is_retryable
from .llm import ModelRuntimeError, OllamaClient, analyze, predict_rules
from .scheduling import aware, moment, runtime_spec

LOGGER = logging.getLogger(__name__)


def record_failure(store, job, code, worker_id, attempt_metadata=None):
    retryable = is_retryable(code)
    options = {"retryable": retryable}
    if attempt_metadata:
        options["attempt_metadata"] = attempt_metadata
    recorded = store.fail_job(job["id"], code, worker_id=worker_id, **options)
    if recorded == "lease_changed" or job["model_kind"] != "llm":
        return
    failure = describe_failure(code)
    if (
        not retryable
        and not failure["service_blocking"]
        and failure["category"] in {"output", "grounding", "input"}
    ):
        course_id = job.get("course_id") or store.get_snapshot(job["state_id"]).presentation_id
        store.record_course_outcome(course_id, code)
        store.set_runtime(
            status="working",
            pause_scope=None,
            last_error_code=None,
            failure_streak=0,
            pause_until=None,
            active_course_id=None,
            active_week=None,
            active_deadline_at=None,
        )
    else:
        prior = store.get_runtime()
        streak = int(prior.get("failure_streak", 0)) + 1
        delay = min(120, 30 * streak) if retryable else 0
        store.set_runtime(
            status="cooldown" if retryable else "paused",
            pause_scope="service",
            last_error_code=code,
            failure_streak=streak,
            pause_until=(moment() + timedelta(seconds=delay)).isoformat() if delay else None,
            active_course_id=None,
            active_week=None,
            active_deadline_at=None,
        )
    LOGGER.warning(
        "Analysis job %s attempt %s failed: %s; automatic retry=%s",
        job["id"],
        job.get("attempts", "?"),
        code,
        retryable,
    )


def process_one(
    store,
    worker_id: str = "",
    *,
    model_kind: str | None = None,
    client: OllamaClient | None = None,
    spec: dict | None = None,
) -> bool:
    """Claim and process one persisted job; True means an attempt was handled.

    Failures are retained by Store. A baseline-only preparation run cannot claim
    an LLM job. The worker identity prevents a superseded lease owner completing
    a job now owned by another worker.
    """
    worker_id = worker_id or f"worker-{uuid.uuid4().hex}"
    timeout = client.config.timeout_seconds if client is not None else 300
    job = store.claim_job(
        worker_id, lease_seconds=max(300, int(timeout) * 2 + 90), model_kind=model_kind
    )
    if job is None:
        return False
    try:
        if (
            job["model_kind"] == "llm"
            and spec is not None
            and not store.job_matches_runtime(job["id"], spec)
        ):
            store.fail_job(job["id"], "ANALYSIS_SUPERSEDED", worker_id=worker_id)
            return True  # Retain history; never run a new prompt under an older job identity.
        snapshot = store.get_snapshot(job["state_id"])
        policy = store.get_policy(snapshot.presentation_id, version=job["policy_version"])
        if job["model_kind"] == "baseline":
            result = predict_rules(snapshot, policy)
        elif job["model_kind"] == "llm":
            store.set_runtime(
                status="working",
                active_course_id=snapshot.presentation_id,
                active_week=snapshot.checkpoint_week,
                active_deadline_at=job.get("lease_until"),
            )
            runtime = client or OllamaClient()
            expected = job.get("expected_model_digest") or job.get("model_digest")
            if expected and runtime.model_digest(timeout=3) != expected:
                raise ModelRuntimeError("MODEL_DIGEST_MISMATCH")
            result = analyze(snapshot, policy, client=runtime)
            if expected and result["inference_performed"] and result["model_digest"] != expected:
                raise ModelRuntimeError("MODEL_DIGEST_MISMATCH")
        else:
            raise ModelRuntimeError("MODEL_KIND_INVALID")
        store.complete_job(job["id"], result, worker_id=worker_id)
        if job["model_kind"] == "llm":
            if result.get("inference_performed"):
                store.record_course_outcome(snapshot.presentation_id)
            store.set_runtime(
                status="working",
                failure_streak=0,
                last_error_code=None,
                pause_until=None,
                pause_scope=None,
                active_course_id=None,
                active_week=None,
                active_deadline_at=None,
            )
    except ModelRuntimeError as error:
        record_failure(store, job, error.code, worker_id, getattr(error, "attempt_metadata", None))
    except (LookupError, ValueError):
        record_failure(store, job, "ANALYSIS_INPUT_OR_LEASE_INVALID", worker_id)
    except SQLAlchemyError:
        # Do not falsely mark a possibly committed result as a failed model run.
        # The durable lease can recover once the database is available again.
        LOGGER.error(
            "Analysis job %s encountered a database error; lease recovery retained", job["id"]
        )
        raise
    except Exception:
        record_failure(store, job, "ANALYSIS_INTERNAL_ERROR", worker_id)
    return True


def run_worker(
    store,
    *,
    once: bool = False,
    poll_seconds: float = 2,
    model_kind: str | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    if not 0.1 <= poll_seconds <= 60:
        raise ValueError("Worker polling must be between 0.1 and 60 seconds.")
    stopped = stop_event or threading.Event()
    LOGGER.info("Checking worker database and checkpoint revisions before accepting work")
    store.ensure_heads()
    if model_kind != "baseline":
        store.migrate_legacy_validation_pause()
    worker_id = f"worker-{uuid.uuid4().hex}"
    last_scan = -30.0
    if threading.current_thread() is threading.main_thread():

        def stop(_signal, _frame):
            stopped.set()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
    LOGGER.info("Analysis worker started with one concurrent inference")
    while not stopped.is_set():
        try:
            if model_kind != "baseline":
                health = store.get_runtime()
                mode = health.get("last_reported_status", health.get("status"))
                pause_until = health.get("pause_until")
                if mode == "paused" or (pause_until and aware(pause_until) > moment()):
                    store.set_runtime(status=mode)
                    if once:
                        return
                    stopped.wait(min(10, poll_seconds))
                    continue
                client = OllamaClient()
                spec = runtime_spec(client)
                if spec["ready"]["status"] != "ready":
                    store.set_runtime(
                        status="waiting_for_model",
                        last_error_code=spec["ready"].get("error_code"),
                        pause_scope="service",
                        active_course_id=None,
                        active_week=None,
                        active_deadline_at=None,
                    )
                    if once:
                        return
                    stopped.wait(15)
                    continue  # Never turn a service outage into hundreds of failed student records.
                if time.monotonic() - last_scan >= 30:
                    discovered = store.discover_analysis(spec)
                    last_scan = time.monotonic()
                    if discovered:
                        LOGGER.info(
                            "Automatically queued %s new/changed learner-week records", discovered
                        )
                store.set_runtime(status="working", pause_until=None, pause_scope=None)
            else:
                client = None
                spec = None
            processed = process_one(
                store, worker_id, model_kind=model_kind, client=client, spec=spec
            )
            if not processed and model_kind != "baseline":
                store.set_runtime(
                    status="idle", active_course_id=None, active_week=None, active_deadline_at=None
                )
        except SQLAlchemyError:
            LOGGER.error("Analysis database unavailable; will retry")
            processed = False
        except ValueError:
            LOGGER.error("Model configuration is invalid; no model jobs were consumed")
            store.set_runtime(
                status="paused",
                last_error_code="MODEL_REQUEST_REJECTED",
                pause_scope="service",
                active_course_id=None,
                active_week=None,
                active_deadline_at=None,
            )
            processed = False
        if once:
            return
        if not processed:
            stopped.wait(poll_seconds)
