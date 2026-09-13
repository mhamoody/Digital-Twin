"""Run paired synthetic operational checks, optionally using the real local Qwen model.

This evaluates output safety and pipeline behaviour, not empirical risk accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.workspace.contracts import CoursePolicy, ModelOutput  # noqa: E402
from digital_twin.workspace.features import degrade_snapshot  # noqa: E402
from digital_twin.workspace.llm import (  # noqa: E402
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
    inference = [row for row in rows if row["inference_performed"]]
    return {
        "attempted_snapshots": len(rows),
        "validated_schema_results": len(returned),
        "grounded_results": sum(row["grounding_valid"] for row in rows),
        "abstentions": sum(row["abstain"] is True for row in rows),
        "pre_inference_abstentions": sum(
            row["abstain"] is True and not row["inference_performed"] for row in rows
        ),
        "inference_performed": len(inference),
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
        "probability_calibration": "Not evaluated; displayed Risk scores are uncalibrated",
    }


def evaluate(seed: int, limit: int, include_llm: bool) -> tuple[dict, list[dict], list[dict]]:
    dataset = generate_dataset(seed=seed, learners_per_course=12, weeks=16)
    states = {(s.presentation_id, s.learner_id, s.checkpoint_week): s for s in dataset["snapshots"]}
    courses = {course["presentation_id"]: course for course in dataset["courses"]}
    samples = []
    # Balance the first 12 samples across all twelve trajectories and all three courses.
    # Checkpoint selection rotates too; final-week-only evaluation misses deadline context.
    for rotation in range(3):
        for index in range(12):
            course_index = (index + rotation) % 3
            enrol = dataset["enrolments"][course_index * 12 + index]
            week = (4, 8, 12, 16)[(index + rotation) % 4]
            samples.append(states[enrol["presentation_id"], enrol["learner_id"], week])
    samples = samples[:limit]
    client = None
    readiness: dict[str, Any] = {"status": "not_requested"}
    if include_llm:
        client = OllamaClient()
        readiness = client.readiness()
        if readiness.get("status") != "ready":
            client = None
    models = [("rules-baseline-v2", predict_rules)]
    if client is not None:
        models.append(
            (client.config.model, lambda snapshot, policy: analyze(snapshot, policy, client))
        )
    rows, examples = [], []
    for base in samples:
        policy = CoursePolicy.model_validate(courses[base.presentation_id]["policy"])
        variants = [("complete", base)] + [
            (mode, degrade_snapshot(base, mode))
            for mode in ("missing_grades", "partial_activity", "stale_activity")
        ]
        for mode, snapshot in variants:
            for model, function in models:
                row = {
                    "model": model,
                    "base_state_id": base.state_id,
                    "state_id": snapshot.state_id,
                    "presentation_id": snapshot.presentation_id,
                    "checkpoint_week": snapshot.checkpoint_week,
                    "fault_mode": mode,
                    "schema_valid": False,
                    "grounding_valid": False,
                    "abstain": None,
                    "abstention_reason": "",
                    "inference_performed": False,
                    "risk_score": None,
                    "risk_band": "",
                    "claim_codes": "",
                    "error_code": "",
                }
                started = time.perf_counter()
                result = None
                try:
                    result = function(snapshot, policy)
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
                    )
                except ModelRuntimeError as error:
                    row["error_code"] = error.code
                except (ValueError, TypeError, KeyError):
                    row["error_code"] = "EVALUATION_CONTRACT_ERROR"
                row["wall_latency_seconds"] = round(time.perf_counter() - started, 6)
                rows.append(row)
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
        "evaluation_version": "workspace-operational-eval-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "demonstration_seed": 2026,
        "reserved_seed": seed != 2026,
        "base_snapshots": len(samples),
        "paired_variants_per_base": 4,
        "dataset_manifest": dataset["manifest"],
        "llm_readiness": readiness,
        "llm_requested": include_llm,
        "llm_executed": client is not None,
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
    args = parser.parse_args()
    if not 1 <= args.limit <= 36:
        parser.error("--limit must be between 1 and 36")
    output = args.output_dir.resolve()
    for filename in ("report.json", "results.csv", "examples.json"):
        if (output / filename).exists():
            parser.error(
                f"Existing report would be overwritten: {output / filename}. "
                "Choose a new --output-dir."
            )
    report, rows, examples = evaluate(args.seed, args.limit, args.llm)
    output.mkdir(parents=True, exist_ok=True)
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
