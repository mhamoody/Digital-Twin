"""Run paired synthetic operational checks, optionally using the real local Qwen model.

This evaluates output safety and pipeline behaviour, not empirical risk accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.workspace.contracts import (  # noqa: E402
    CoursePolicy,
    LearnerSnapshot,
    ModelOutput,
    digest,
)
from digital_twin.workspace.errors import ERRORS  # noqa: E402
from digital_twin.workspace.features import degrade_snapshot  # noqa: E402
from digital_twin.workspace.llm import (  # noqa: E402
    PROMPT_VERSION,
    ModelRuntimeError,
    OllamaClient,
    analyze,
    predict_rules,
    validate_output,
)
from digital_twin.workspace.synthetic import generate_dataset  # noqa: E402


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    left = math.floor(position)
    right = math.ceil(position)
    return round(ordered[left] + (ordered[right] - ordered[left]) * (position - left), 6)


def summarize(rows: list[dict]) -> dict:
    returned = [row for row in rows if row["schema_valid"]]
    attempted = [row for row in rows if row["generation_attempts"]]
    inference = [row for row in rows if row["inference_performed"]]
    generations = [attempt for row in rows for attempt in row["attempt_metadata"]]
    repairs = [attempt for attempt in generations if attempt["attempt"] > 1]
    return {
        "attempted_snapshots": len(rows),
        "validated_schema_results": len(returned),
        "grounded_results": sum(row["grounding_valid"] for row in rows),
        "abstentions": sum(row["abstain"] is True for row in rows),
        "pre_inference_abstentions": sum(
            row["abstain"] is True and not row["inference_performed"] for row in rows
        ),
        "inference_performed": len(inference),
        "generation_attempted_cases": len(attempted),
        "accepted_pipeline_results": len(returned),
        "accepted_pipeline_fraction": len(returned) / len(rows) if rows else None,
        "outcomes": dict(Counter(row["outcome"] for row in rows)),
        "first_pass_validated": sum(row["outcome"] == "first_pass_validated" for row in rows),
        "repaired_validated": sum(row["outcome"] == "repaired_validated" for row in rows),
        "model_abstentions": sum(row["outcome"] == "model_abstention" for row in rows),
        "final_rejected": sum(row["outcome"] == "final_rejected" for row in rows),
        "runtime_failed": sum(row["outcome"] == "runtime_failure" for row in rows),
        "generation_attempts": len(generations),
        "repair_generations": len(repairs),
        "rejected_generations": sum(attempt["outcome"] == "rejected" for attempt in generations),
        "generation_error_counts": dict(
            Counter(attempt["error_code"] for attempt in generations if attempt["error_code"])
        ),
        "repair_generation_seconds": round(
            sum(attempt["latency_seconds"] for attempt in repairs), 6
        ),
        "errors": dict(Counter(row["error_code"] for row in rows if row["error_code"])),
        "schema_success_per_attempt": len(returned) / len(rows) if rows else None,
        "grounding_success_per_attempt": sum(row["grounding_valid"] for row in rows) / len(rows)
        if rows
        else None,
        "wall_latency_p50_seconds": percentile([row["wall_latency_seconds"] for row in rows], 0.5),
        "wall_latency_p95_seconds": percentile([row["wall_latency_seconds"] for row in rows], 0.95),
        "inference_latency_p50_seconds": percentile(
            [row["wall_latency_seconds"] for row in inference], 0.5
        ),
        "inference_latency_p95_seconds": percentile(
            [row["wall_latency_seconds"] for row in inference], 0.95
        ),
        "attempted_model_job_latency_p50_seconds": percentile(
            [row["wall_latency_seconds"] for row in attempted], 0.5
        ),
        "attempted_model_job_latency_p95_seconds": percentile(
            [row["wall_latency_seconds"] for row in attempted], 0.95
        ),
        "generation_latency_p50_seconds": percentile(
            [a["latency_seconds"] for a in generations], 0.5
        ),
        "generation_latency_p95_seconds": percentile(
            [a["latency_seconds"] for a in generations], 0.95
        ),
        "latency_denominators": {
            "all_case_wall_times": len(rows),
            "inference_job_wall_times": len(inference),
            "attempted_model_job_wall_times_including_runtime_failures": len(attempted),
            "generation_times_including_rejections_and_runtime_errors": len(generations),
            "repair_generation_times": len(repairs),
        },
        "probability_calibration": "Not evaluated; displayed Risk scores are uncalibrated",
    }


def frozen_cases(seed: int, limit: int) -> dict:
    """Freeze stratified complete and degraded evidence before inference or tuning."""
    dataset = generate_dataset(seed=seed, learners_per_course=12, weeks=16)
    states = {(s.presentation_id, s.learner_id, s.checkpoint_week): s for s in dataset["snapshots"]}
    courses = {course["presentation_id"]: course for course in dataset["courses"]}
    oracle = {
        (row["presentation_id"], row["learner_id"]): row["trajectory"] for row in dataset["oracle"]
    }
    samples = []
    # Balance the first 12 samples across all twelve trajectories and all three courses.
    # Checkpoint selection rotates too; final-week-only evaluation misses deadline context.
    for rotation in range(3):
        for index in range(12):
            course_index = (index + rotation) % 3
            enrol = dataset["enrolments"][course_index * 12 + index]
            week = (4, 8, 12, 16)[(index + rotation) % 4]
            samples.append(states[enrol["presentation_id"], enrol["learner_id"], week])
    cases = []
    for base in samples[:limit]:
        variants = [("complete", base)] + [
            (mode, degrade_snapshot(base, mode))
            for mode in ("missing_grades", "partial_activity", "stale_activity")
        ]
        for mode, snapshot in variants:
            # Scenario stratum belongs only to the evaluation manifest, never to snapshot/prompt.
            cases.append(
                {
                    "base_state_id": base.state_id,
                    "snapshot": snapshot.model_dump(mode="json"),
                    "policy": courses[base.presentation_id]["policy"],
                    "fault_mode": mode,
                    "scenario_family": oracle[base.presentation_id, base.learner_id],
                }
            )
    return {
        "schema_version": "workspace-evaluation-inputs-v2",
        "seed": seed,
        "dataset_manifest": dataset["manifest"],
        "cases": cases,
        "input_hash": digest(cases),
    }


def validate_frozen_inputs(value: dict) -> dict:
    if value.get("schema_version") != "workspace-evaluation-inputs-v2":
        raise ValueError("Unsupported frozen evaluation input schema")
    cases = value.get("cases", [])
    if not cases or len(cases) > 144 or value.get("input_hash") != digest(cases):
        raise ValueError("Frozen evaluation input count or checksum is invalid")
    identities = set()
    for case in cases:
        snapshot = LearnerSnapshot.model_validate(case["snapshot"])
        CoursePolicy.model_validate(case["policy"])
        if snapshot.data_origin != "synthetic":
            raise ValueError("This harness only exports synthetic evaluation inputs")
        if case["fault_mode"] not in {
            "complete",
            "missing_grades",
            "partial_activity",
            "stale_activity",
        }:
            raise ValueError("Unknown fault fixture")
        identity = snapshot.state_id, digest(case["policy"])
        if identity in identities:
            raise ValueError("Duplicate frozen evaluation case")
        identities.add(identity)
    return value


def safe_attempts(records: list[dict]) -> list[dict]:
    """Only measured counters, error codes, and output hashes reach exported traces."""
    result = []
    for index, raw in enumerate(records):
        latency = raw.get("latency_seconds", 0)
        latency = (
            float(latency) if isinstance(latency, (int, float)) and math.isfinite(latency) else 0
        )
        output_hash = raw.get("output_hash")
        result.append(
            {
                "attempt": index + 1,
                "kind": "initial" if index == 0 else "validation_feedback",
                "outcome": raw.get("outcome")
                if raw.get("outcome") in {"validated", "rejected", "runtime_error"}
                else "unknown",
                "error_code": raw.get("error_code")
                if raw.get("error_code") in ERRORS
                else "UNKNOWN_ERROR"
                if raw.get("error_code")
                else None,
                "latency_seconds": max(0, latency),
                "output_hash": output_hash
                if isinstance(output_hash, str) and re.fullmatch(r"[0-9a-f]{64}", output_hash)
                else None,
                "runtime": {
                    key: val
                    for key, val in raw.get("runtime", {}).items()
                    if key in {"prompt_eval_count", "eval_count", "load_duration", "total_duration"}
                    and type(val) is int
                    and val >= 0
                },
            }
        )
    return result


def evaluate(
    seed: int, limit: int, include_llm: bool, *, inputs: dict | None = None, progress: Any = None
) -> tuple[dict, list[dict], list[dict]]:
    pack = validate_frozen_inputs(inputs or frozen_cases(seed, limit))
    client = None
    readiness: dict[str, Any] = {"status": "not_requested"}
    if include_llm:
        try:
            client = OllamaClient()
            readiness = client.readiness()
        except ValueError:
            readiness = {"status": "configuration_error"}
        if readiness.get("status") != "ready":
            client = None
    models = [("rules-baseline-v2", predict_rules)]
    if client is not None:
        models.append(
            (client.config.model, lambda snapshot, policy: analyze(snapshot, policy, client))
        )
    rows, examples = [], []
    for case in pack["cases"]:
        snapshot = LearnerSnapshot.model_validate(case["snapshot"])
        policy = CoursePolicy.model_validate(case["policy"])
        mode = case["fault_mode"]
        for model, function in models:
            row = {
                "model": model,
                "base_state_id": case["base_state_id"],
                "state_id": snapshot.state_id,
                "presentation_id": snapshot.presentation_id,
                "checkpoint_week": snapshot.checkpoint_week,
                "fault_mode": mode,
                "scenario_family": case.get("scenario_family", "unspecified"),
                "schema_valid": False,
                "grounding_valid": False,
                "abstain": None,
                "abstention_reason": "",
                "inference_performed": False,
                "risk_score": None,
                "risk_band": "",
                "claim_codes": "",
                "error_code": "",
                "outcome": "runtime_failure",
                "generation_attempts": 0,
                "attempt_metadata": [],
                "model_digest": None,
                "prompt_version": None,
            }
            started = time.perf_counter()
            result = None
            try:
                result = function(snapshot, policy)
                row["attempt_metadata"] = safe_attempts(result.get("inference_attempts", []))
                parsed = ModelOutput.model_validate(result["output"])
                row["schema_valid"] = True
                validate_output(parsed, snapshot, policy)
                row.update(
                    grounding_valid=True,
                    abstain=parsed.abstain,
                    abstention_reason=parsed.abstention_reason or "",
                    inference_performed=result.get("inference_performed", False),
                    risk_score=parsed.risk_score,
                    risk_band=parsed.risk_band or "",
                    claim_codes="|".join(claim.code for claim in parsed.claims),
                    model_digest=result.get("model_digest"),
                    prompt_version=result.get("prompt_version"),
                )
                if parsed.abstain:
                    row["outcome"] = (
                        "model_abstention"
                        if row["attempt_metadata"]
                        else "pre_inference_abstention"
                    )
                elif model == "rules-baseline-v2":
                    row["outcome"] = "baseline_validated"
                else:
                    row["outcome"] = (
                        "repaired_validated"
                        if len(row["attempt_metadata"]) > 1
                        else "first_pass_validated"
                    )
            except ModelRuntimeError as error:
                row["error_code"] = error.code
                row["attempt_metadata"] = safe_attempts(getattr(error, "attempt_metadata", []))
                category = ERRORS[error.code].category if error.code in ERRORS else "internal"
                row["outcome"] = (
                    "final_rejected" if category in {"output", "grounding"} else "runtime_failure"
                )
            except (ValueError, TypeError, KeyError):
                row["error_code"] = "EVALUATION_CONTRACT_ERROR"
                row["outcome"] = "final_rejected"
            row["generation_attempts"] = len(row["attempt_metadata"])
            row["inference_performed"] = any(a["output_hash"] for a in row["attempt_metadata"])
            row["wall_latency_seconds"] = round(time.perf_counter() - started, 6)
            rows.append(row)
            if progress:
                progress(row)
            if len(examples) < 8 and mode == "complete":
                examples.append(
                    {
                        "snapshot": snapshot.model_dump(mode="json"),
                        "model": model,
                        "result": result,
                        "error_code": row["error_code"],
                    }
                )
    report = {
        "evaluation_version": "workspace-operational-eval-v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": pack["seed"],
        "input_hash": pack["input_hash"],
        "prompt_version": PROMPT_VERSION,
        "demonstration_seed": 2026,
        "reserved_seed": pack["seed"] != 2026,
        "base_snapshots": len({case["base_state_id"] for case in pack["cases"]}),
        "paired_variants_per_base": 4,
        "dataset_manifest": pack["dataset_manifest"],
        "scenario_family_counts": dict(
            Counter(
                case["scenario_family"]
                for case in pack["cases"]
                if case["fault_mode"] == "complete"
            )
        ),
        "llm_readiness": readiness,
        "llm_requested": include_llm,
        "llm_client_ready": client is not None,
        "llm_executed": any(row["inference_performed"] for row in rows),
        "models": {
            model: summarize([row for row in rows if row["model"] == model])
            for model, _function in models
        },
        "by_fault": {
            model: {
                mode: summarize(
                    [row for row in rows if row["model"] == model and row["fault_mode"] == mode]
                )
                for mode in ("complete", "missing_grades", "partial_activity", "stale_activity")
            }
            for model, _function in models
        },
        "interpretation": [
            "Synthetic operational behaviour only; "
            "no empirical accuracy, F1, AUC or causal-effect claims.",
            "A new seed reserves numeric histories; "
            "scenario families are shared, not unseen-family validation.",
            "Schema success includes gate-produced abstentions. "
            "It is not a raw-LLM JSON success rate.",
            "No numeric Risk score target is derived from the rules baseline "
            "or the private scenario oracle.",
            "Missing local model reports readiness failure; "
            "no synthetic LLM predictions replace it.",
            "Grounding checks validate factual citations and allowed actions, "
            "not calibrated risk magnitude.",
            "First-pass/repaired counts are accepted scored outputs; "
            "model abstentions are separate outcomes.",
            "Inference performed requires a returned output hash, not merely a ready service "
            "or attempted request. A timed-out request may have executed remotely; "
            "that is unknown.",
            "Attempted-model-job latency includes failed requests, all correction attempts and "
            "validation. Inference latency covers only jobs with a returned output; neither "
            "measures time on a GPU alone. Both denominators are reported.",
            "Repair overhead reports measured second-generation time, "
            "without excluding first-generation rejection.",
        ],
    }
    return report, rows, examples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument(
        "--limit", type=int, default=24, help="1..36 balanced base snapshots; each has 4 variants."
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Run real local Qwen inference if model readiness passes.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/workspace/evaluation"))
    parser.add_argument(
        "--inputs", type=Path, help="Reuse a previous inputs.json frozen evidence pack"
    )
    args = parser.parse_args()
    if not 1 <= args.limit <= 36:
        parser.error("--limit must be between 1 and 36")
    output = args.output_dir.resolve()
    for filename in ("report.json", "results.csv", "examples.json", "inputs.json"):
        if (output / filename).exists():
            parser.error(
                f"Existing report would be overwritten: {output / filename}. "
                "Choose a new --output-dir."
            )
    pack = (
        validate_frozen_inputs(json.loads(args.inputs.read_text(encoding="utf-8")))
        if args.inputs
        else frozen_cases(args.seed, args.limit)
    )
    output.mkdir(parents=True, exist_ok=True)
    # Freeze before inference; even an interrupted run retains its exact input fixture.
    with (output / "inputs.json").open("x", encoding="utf-8") as stream:
        json.dump(pack, stream, indent=2)

    def progress(row):
        print(
            f"{row['model']} / {row['fault_mode']}: {row['outcome']}; "
            f"{row['generation_attempts']} generation attempt(s)",
            flush=True,
        )

    report, rows, examples = evaluate(
        args.seed, args.limit, args.llm, inputs=pack, progress=progress
    )
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
    with (output / "results.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (output / "examples.json").open("x", encoding="utf-8") as stream:
        json.dump(examples, stream, indent=2)
    print(
        json.dumps(
            {
                "report": str(output / "report.json"),
                "models": report["models"],
                "llm_readiness": report["llm_readiness"],
            },
            indent=2,
        )
    )
    return 2 if args.llm and not report["llm_executed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
