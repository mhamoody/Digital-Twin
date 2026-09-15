"""Bounded, allowlisted generation metadata safe to retain for operator diagnosis."""

import math
import re
import uuid
from datetime import UTC, datetime

from .errors import describe_failure
from .models import InferenceTrace


def safe_attempts(attempts):
    result = []
    if not isinstance(attempts, list):
        return result
    for index, item in enumerate(attempts[:2], 1):
        if not isinstance(item, dict):
            continue
        duration = item.get("latency_seconds")
        valid_number = isinstance(duration, (int, float)) and not isinstance(duration, bool)
        output_hash = item.get("output_hash")
        runtime = item.get("runtime", {})
        runtime = runtime if isinstance(runtime, dict) else {}
        result.append(
            {
                "attempt": index,
                "kind": "initial" if index == 1 else "validation_feedback",
                "outcome": item.get("outcome")
                if item.get("outcome") in {"validated", "rejected", "runtime_error"}
                else "rejected",
                "error_code": describe_failure(item["error_code"])["code"]
                if item.get("error_code")
                else None,
                "latency_seconds": duration
                if valid_number and math.isfinite(duration) and duration >= 0
                else None,
                "output_hash": output_hash
                if isinstance(output_hash, str) and re.fullmatch(r"[0-9a-f]{64}", output_hash)
                else None,
                "runtime": {
                    key: runtime[key]
                    for key in (
                        "prompt_eval_count",
                        "eval_count",
                        "load_duration",
                        "total_duration",
                    )
                    if isinstance(runtime.get(key), int)
                    and not isinstance(runtime[key], bool)
                    and runtime[key] >= 0
                },
            }
        )
    return result


def persist_traces(session, job, attempts):
    for record in safe_attempts(attempts):
        session.add(
            InferenceTrace(
                id=uuid.uuid4().hex,
                job_id=job.id,
                job_attempt=job.attempts,
                generation=record["attempt"],
                payload=record,
                created_at=datetime.now(UTC),
            )
        )
