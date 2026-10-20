"""Inspect one saved model job; optional isolated replay never changes the job queue.

Historical raw replies are not retained by the application. A replay is a new
request using saved evidence/policy and the current prompt implementation.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.persistence.database import create_twin_engine  # noqa: E402
from digital_twin.workspace import llm  # noqa: E402
from digital_twin.workspace.contracts import CoursePolicy, LearnerSnapshot, digest  # noqa: E402
from digital_twin.workspace.errors import ERRORS  # noqa: E402
from digital_twin.workspace.models import (  # noqa: E402
    Analysis,
    AnalysisJob,
    AnalysisPlan,
    InferenceTrace,
    Policy,
    Snapshot,
)
from digital_twin.workspace.output_contract import safe_validation_details  # noqa: E402
from digital_twin.workspace.tracing import safe_attempts  # noqa: E402

HASH_PATTERN = re.compile(r"(?:sha256:)?[a-fA-F0-9]{64}")
CONFIG_KEYS = {
    "DIGITAL_TWIN_DATABASE_URL",
    "DIGITAL_TWIN_OLLAMA_URL",
    "DIGITAL_TWIN_LLM_MODEL",
    "DIGITAL_TWIN_LLM_DIGEST",
    "DIGITAL_TWIN_LLM_TIMEOUT_SECONDS",
    "DIGITAL_TWIN_LLM_CONTEXT",
    "DIGITAL_TWIN_LLM_MAX_TOKENS",
}


class DiagnosticError(RuntimeError):
    """Static operator-facing code; never copies a database URL or model payload."""


def safe_hash(value: Any) -> str | None:
    return value if isinstance(value, str) and HASH_PATTERN.fullmatch(value) else None


def safe_code(value: Any) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) and value in ERRORS else "UNRECOGNIZED_ERROR_CODE"


def safe_details(value: Any) -> list[dict]:
    """Retain field/error structure, never Pydantic input values or free-text messages."""
    return safe_validation_details(value)


def safe_trace(payload: dict) -> dict:
    sanitized = safe_attempts([payload])
    if not sanitized:
        return {}
    result = sanitized[0]
    if payload.get("attempt") == 2:
        result.update(attempt=2, kind="validation_feedback")
    return result


@dataclass
class SavedJob:
    summary: dict
    snapshot: LearnerSnapshot
    policy: CoursePolicy
    historical_digest: str | None


def load_saved_job(engine: Any, job_id: str) -> SavedJob:
    if not re.fullmatch(r"[a-f0-9]{64}", job_id):
        raise DiagnosticError("INVALID_JOB_ID")
    schema = None if engine.dialect.name == "sqlite" else "analytics"
    tables = set(inspect(engine).get_table_names(schema=schema))
    required = {"workspace_analysis_job", "workspace_snapshot", "workspace_policy"}
    if not required.issubset(tables):
        raise DiagnosticError("WORKSPACE_SCHEMA_MISSING")
    audit_schema = None if engine.dialect.name == "sqlite" else "audit"
    audit_tables = set(inspect(engine).get_table_names(schema=audit_schema))
    with Session(engine, autoflush=False) as session:
        if engine.dialect.name == "postgresql":
            session.execute(text("SET TRANSACTION READ ONLY"))
        job = session.get(AnalysisJob, job_id)
        if job is None:
            raise DiagnosticError("JOB_NOT_FOUND")
        stored = session.get(Snapshot, job.state_id)
        if stored is None:
            raise DiagnosticError("SAVED_SNAPSHOT_MISSING")
        snapshot = LearnerSnapshot.model_validate(stored.payload)
        policy_row = session.get(Policy, (snapshot.presentation_id, job.policy_version))
        if policy_row is None:
            raise DiagnosticError("SAVED_POLICY_MISSING")
        policy = CoursePolicy.model_validate(policy_row.payload)
        plan = session.get(AnalysisPlan, job_id) if "workspace_analysis_plan" in tables else None
        analysis = session.get(Analysis, job_id) if "workspace_analysis" in tables else None
        historical_digest = safe_hash(job.expected_model_digest)
        if not historical_digest and analysis:
            historical_digest = safe_hash(analysis.payload.get("model_digest"))
        traces = []
        if "workspace_inference_trace" in audit_tables:
            for trace in session.scalars(
                select(InferenceTrace)
                .where(InferenceTrace.job_id == job_id)
                .order_by(InferenceTrace.job_attempt, InferenceTrace.generation)
            ):
                traces.append(
                    {
                        "job_attempt": trace.job_attempt,
                        "generation": trace.generation,
                        "created_at": trace.created_at.isoformat(),
                        **safe_trace(trace.payload),
                    }
                )
        summary = {
            "diagnostic_version": "saved-model-job-inspection-v1",
            "job_id": job_id,
            "job_status": job.status,
            "job_error_code": safe_code(job.error_code),
            "worker_attempts": job.attempts,
            "checkpoint_week": snapshot.checkpoint_week,
            "data_origin": snapshot.data_origin,
            "policy_version": job.policy_version,
            "model_kind": job.model_kind,
            "historical_model_digest": historical_digest,
            "historical_plan_fingerprint": safe_hash(plan.fingerprint) if plan else None,
            "snapshot_hash": digest(snapshot),
            "policy_hash": digest(policy),
            "updated_at": job.updated_at.isoformat(),
            "saved_generation_traces": traces,
            "historical_raw_reply": "Not stored; cannot recover the original reply from hashes.",
            "database_mutated": False,
            "replay_requested": False,
            "privacy": "No learner names/IDs, raw evidence, account secrets, "
            "or raw replies by default.",
        }
    return SavedJob(summary, snapshot, policy, historical_digest)


class CapturingClient(llm.OllamaClient):
    """At most two new generations. Capture is possible only after origin checks."""

    def __init__(self, config: llm.RuntimeConfig, *, capture: bool = False, transport=None):
        super().__init__(config, transport=transport)
        self.capture = capture
        self.generation_count = 0
        self.captured: list[dict] = []

    def generate(self, *, system: str, prompt: str, schema: dict):
        if self.generation_count >= 2:
            raise DiagnosticError("DIAGNOSTIC_GENERATION_LIMIT_REACHED")
        self.generation_count += 1
        try:
            raw, model_digest, runtime = super().generate(
                system=system, prompt=prompt, schema=schema
            )
        except llm.ModelRuntimeError as error:
            if self.capture:
                self.captured.append(
                    {
                        "generation": self.generation_count,
                        "raw_reply": None,
                        "note": "Runtime returned no capturable validated response envelope.",
                        "error_code": safe_code(error.code),
                        "output_hash": safe_hash(
                            getattr(error, "response_metadata", {}).get("output_hash")
                        ),
                    }
                )
            raise
        if self.capture:
            encoded = raw.encode("utf-8")
            self.captured.append(
                {
                    "generation": self.generation_count,
                    "raw_reply": encoded[:65536].decode("utf-8", errors="ignore"),
                    "truncated_for_package": len(encoded) > 65536,
                    "output_hash": digest(raw),
                }
            )
        return raw, model_digest, runtime


def inspect_replay(
    saved: SavedJob,
    client: CapturingClient,
    *,
    allow_current_runtime: bool = False,
    capture_synthetic_output: bool = False,
) -> tuple[dict, dict]:
    """A new model experiment, not a queue retry or recovery of a historical reply."""
    if saved.summary["model_kind"] != "llm":
        raise DiagnosticError("REPLAY_REQUIRES_SAVED_LLM_JOB")
    if capture_synthetic_output and saved.snapshot.data_origin != "synthetic":
        raise DiagnosticError("RAW_CAPTURE_REQUIRES_SYNTHETIC_ORIGIN")
    if client.capture and not capture_synthetic_output:
        raise DiagnosticError("RAW_CAPTURE_NOT_AUTHORIZED")
    readiness = client.readiness()
    if readiness.get("status") != "ready":
        raise DiagnosticError(safe_code(readiness.get("error_code")) or "MODEL_NOT_READY")
    current_digest = safe_hash(readiness.get("digest"))
    if current_digest is None:
        raise DiagnosticError("CURRENT_MODEL_DIGEST_INVALID")
    same_digest = saved.historical_digest == current_digest
    if not same_digest and not allow_current_runtime:
        raise DiagnosticError(
            "HISTORICAL_MODEL_DIGEST_UNKNOWN"
            if not saved.historical_digest
            else "HISTORICAL_MODEL_DIGEST_MISMATCH"
        )
    # Pin the checked current identity for the entire diagnostic, including its repair.
    client.config = replace(client.config, expected_digest=current_digest)
    report = copy.deepcopy(saved.summary)
    current_fingerprint = digest(
        [
            client.config.model,
            llm.PROMPT_VERSION,
            client.config.context_tokens,
            client.config.max_tokens,
        ]
    )
    report.update(
        replay_requested=True,
        replay_kind="new inference with saved evidence/policy and current prompt",
        current_model=client.config.model,
        current_model_digest=current_digest,
        historical_model_digest_matches=same_digest,
        current_prompt_version=llm.PROMPT_VERSION,
        current_runtime_fingerprint=current_fingerprint,
        historical_plan_matches=current_fingerprint == saved.summary["historical_plan_fingerprint"],
        performed_at=datetime.now(UTC).isoformat(),
        raw_capture_requested=capture_synthetic_output,
    )
    private_files = {}
    if capture_synthetic_output:
        system, prompt, schema, _aliases = llm.build_prompt(saved.snapshot, saved.policy)
        private_files["prepared_prompt.json"] = {
            "origin": "synthetic",
            "system": system,
            "prompt": json.loads(prompt),
            "output_schema": schema,
        }
    try:
        result = llm.analyze(saved.snapshot, saved.policy, client)
        output = result["output"]
        report["replay"] = {
            "status": result.get("validation_outcome", "validated"),
            "risk_score": output["risk_score"],
            "risk_band": output["risk_band"],
            "abstain": output["abstain"],
            "abstention_reason": output.get("abstention_reason"),
            "claim_codes": [claim["code"] for claim in output["claims"]],
            "suggested_actions": output["suggested_actions"],
            "inference_performed": result.get("inference_performed", False),
            "generation_attempts": [
                safe_trace(attempt) for attempt in result.get("inference_attempts", [])
            ],
        }
    except llm.ModelRuntimeError as error:
        report["replay"] = {
            "status": "rejected",
            "error_code": safe_code(error.code),
            "generation_attempts": [safe_trace(attempt) for attempt in error.attempt_metadata],
        }
    if capture_synthetic_output:
        private_files["synthetic_replies.json"] = {
            "origin": "synthetic",
            "historical_reply": False,
            "generations": client.captured,
            "note": "These are newly generated diagnostic replies, "
            "not the historical failed answers.",
        }
    report["new_generation_requests"] = client.generation_count
    return report, private_files


def configured_values(project_root: Path, environ: dict[str, str] | None = None) -> dict[str, str]:
    """Read simple quoted deployment assignments without executing shell code."""
    values = dict(os.environ if environ is None else environ)
    path = Path(values.get("DIGITAL_TWIN_ENV_FILE", str(project_root / ".env.lobot")))
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            key, separator, raw = line.partition("=")
            if not separator or key.strip() not in CONFIG_KEYS:
                continue
            try:
                parsed = shlex.split(raw, comments=True, posix=True)
            except ValueError as error:
                raise DiagnosticError("DEPLOYMENT_CONFIGURATION_PARSE_FAILED") from error
            if len(parsed) > 1:
                raise DiagnosticError("DEPLOYMENT_CONFIGURATION_PARSE_FAILED")
            values[key.strip()] = parsed[0] if parsed else ""
    manifest = project_root / "var" / "models" / "predictor.json"
    if manifest.is_file():
        try:
            saved = json.loads(manifest.read_text(encoding="utf-8"))
        except (ValueError, OSError) as error:
            raise DiagnosticError("MODEL_MANIFEST_INVALID") from error
        if not isinstance(saved, dict):
            raise DiagnosticError("MODEL_MANIFEST_INVALID")
        model_digest = safe_hash(saved.get("digest"))
        if model_digest is None:
            raise DiagnosticError("MODEL_MANIFEST_DIGEST_INVALID")
        values["DIGITAL_TWIN_LLM_DIGEST"] = model_digest
    return values


def runtime_config(values: dict[str, str]) -> llm.RuntimeConfig:
    try:
        return llm.RuntimeConfig(
            base_url=values.get("DIGITAL_TWIN_OLLAMA_URL", "http://127.0.0.1:11434"),
            model=values.get("DIGITAL_TWIN_LLM_MODEL", "qwen2.5:7b"),
            expected_digest=values.get("DIGITAL_TWIN_LLM_DIGEST") or None,
            timeout_seconds=float(values.get("DIGITAL_TWIN_LLM_TIMEOUT_SECONDS", "120")),
            context_tokens=int(values.get("DIGITAL_TWIN_LLM_CONTEXT", "8192")),
            max_tokens=int(values.get("DIGITAL_TWIN_LLM_MAX_TOKENS", "1200")),
        )
    except ValueError as error:
        raise DiagnosticError("MODEL_CONFIGURATION_INVALID") from error


def read_only_engine(database_url: str, project_root: Path):
    try:
        url = make_url(database_url)
        if url.drivername.startswith("sqlite"):
            if url.database in (None, "", ":memory:"):
                raise DiagnosticError("SAVED_DATABASE_FILE_REQUIRED")
            source = Path(url.database)
            if not source.is_absolute():
                source = project_root / source
            source = source.resolve()
            if not source.is_file():
                raise DiagnosticError("DATABASE_FILE_NOT_FOUND")
            url = url.set(database="file:" + source.as_posix(), query={"mode": "ro", "uri": "true"})
        elif not url.drivername.startswith("postgresql"):
            raise DiagnosticError("DATABASE_BACKEND_UNSUPPORTED")
        return create_twin_engine(url.render_as_string(hide_password=False))
    except (ValueError, SQLAlchemyError) as error:
        raise DiagnosticError("DATABASE_CONFIGURATION_INVALID") from error


def write_package(directory: Path, summary: dict, private_files: dict) -> None:
    if directory.exists():
        raise DiagnosticError("OUTPUT_DIRECTORY_ALREADY_EXISTS")
    directory.mkdir(parents=True, mode=0o700)
    directory.chmod(0o700)
    for filename, value in {"summary.json": summary, **private_files}.items():
        descriptor = os.open(directory / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, help="Saved 64-character job hash from diagnostics")
    parser.add_argument("--database-url", help="Normally read from .env.lobot; never printed")
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Make at most two new local generations; saved job stays unchanged",
    )
    parser.add_argument(
        "--allow-current-runtime",
        action="store_true",
        help="Allow a current-model experiment when historical weights differ or are unknown",
    )
    parser.add_argument(
        "--capture-synthetic-output",
        action="store_true",
        help="Save synthetic replies/prompt privately; requires --replay and --output-dir",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="New private diagnostic directory; existing directories are refused",
    )
    args = parser.parse_args()
    if args.allow_current_runtime and not args.replay:
        parser.error("--allow-current-runtime requires --replay")
    if args.capture_synthetic_output and (not args.replay or not args.output_dir):
        parser.error("--capture-synthetic-output requires --replay and --output-dir")
    engine = None
    try:
        if args.output_dir and args.output_dir.exists():
            raise DiagnosticError("OUTPUT_DIRECTORY_ALREADY_EXISTS")
        values = configured_values(ROOT)
        database_url = args.database_url or values.get("DIGITAL_TWIN_DATABASE_URL")
        if not database_url:
            raise DiagnosticError("DATABASE_CONFIGURATION_MISSING")
        engine = read_only_engine(database_url, ROOT)
        saved = load_saved_job(engine, args.job)
        summary, private_files = saved.summary, {}
        if args.replay:
            if args.capture_synthetic_output and saved.snapshot.data_origin != "synthetic":
                raise DiagnosticError("RAW_CAPTURE_REQUIRES_SYNTHETIC_ORIGIN")
            client = CapturingClient(runtime_config(values), capture=args.capture_synthetic_output)
            summary, private_files = inspect_replay(
                saved,
                client,
                allow_current_runtime=args.allow_current_runtime,
                capture_synthetic_output=args.capture_synthetic_output,
            )
        if args.output_dir:
            write_package(args.output_dir.resolve(), summary, private_files)
            summary = {**summary, "diagnostic_package_saved": True}
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 3 if summary.get("replay", {}).get("status") == "rejected" else 0
    except DiagnosticError as error:
        print(json.dumps({"error_code": str(error), "database_mutated": False}))
        return 2
    except (SQLAlchemyError, OSError, ValueError, ImportError):
        print(
            json.dumps(
                {"error_code": "DIAGNOSTIC_CONFIGURATION_OR_READ_FAILED", "database_mutated": False}
            )
        )
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
