"""One-process durable inference worker, independently restartable from the UI."""

from __future__ import annotations

import logging
import signal
import threading
import uuid

from sqlalchemy.exc import SQLAlchemyError

from .llm import ModelRuntimeError, OllamaClient, analyze, predict_rules

LOGGER = logging.getLogger(__name__)


def process_one(
    store, worker_id: str = "", *, model_kind: str | None = None, client: OllamaClient | None = None
) -> bool:
    """Claim and process one persisted job; True means an attempt was handled.

    Failures are retained by Store. A baseline-only preparation run cannot claim
    an LLM job. The worker identity prevents a superseded lease owner completing
    a job now owned by another worker.
    """
    worker_id = worker_id or f"worker-{uuid.uuid4().hex}"
    timeout = client.config.timeout_seconds if client is not None else 300
    job = store.claim_job(
        worker_id, lease_seconds=max(300, int(timeout) + 30), model_kind=model_kind
    )
    if job is None:
        return False
    try:
        snapshot = store.get_snapshot(job["state_id"])
        policy = store.get_policy(snapshot.presentation_id, version=job["policy_version"])
        if job["model_kind"] == "baseline":
            result = predict_rules(snapshot, policy)
        elif job["model_kind"] == "llm":
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
    except ModelRuntimeError as error:
        store.fail_job(job["id"], error.code, worker_id=worker_id)
        LOGGER.warning("Analysis job %s failed: %s", job["id"], error.code)
    except (LookupError, ValueError):
        store.fail_job(job["id"], "ANALYSIS_INPUT_OR_LEASE_INVALID", worker_id=worker_id)
        LOGGER.warning("Analysis job %s could not be completed: input or lease changed", job["id"])
    except SQLAlchemyError:
        # Do not falsely mark a possibly committed result as a failed model run.
        # The durable lease can recover once the database is available again.
        LOGGER.error(
            "Analysis job %s encountered a database error; lease recovery retained", job["id"]
        )
        raise
    except Exception:
        store.fail_job(job["id"], "ANALYSIS_INTERNAL_ERROR", worker_id=worker_id)
        LOGGER.error("Analysis job %s failed: ANALYSIS_INTERNAL_ERROR", job["id"])
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
    worker_id = f"worker-{uuid.uuid4().hex}"
    if threading.current_thread() is threading.main_thread():

        def stop(_signal, _frame):
            stopped.set()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
    LOGGER.info("Analysis worker started with one concurrent inference")
    while not stopped.is_set():
        try:
            processed = process_one(store, worker_id, model_kind=model_kind)
        except SQLAlchemyError:
            LOGGER.error("Analysis database unavailable; will retry")
            processed = False
        if once:
            return
        if not processed:
            stopped.wait(poll_seconds)
