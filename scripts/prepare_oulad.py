"""Prepare one real OULAD presentation for the integration-demo vertical slice.

The script never modifies ``OULAD/``. Genuine missing values stay null with an
explicit reason. The only synthesized field is a separate, clearly labelled
calendar anchor for later Moodle replay; no empirical behaviour, score, outcome,
or fine-grained timestamp is fabricated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


SOURCE_ID = "oulad-2015-release"
MISSING = {"", "?"}

ACTIVITY_TAXONOMY = {
    "resource": "content",
    "subpage": "content",
    "oucontent": "content",
    "url": "content",
    "page": "content",
    "homepage": "content",
    "folder": "content",
    "htmlactivity": "content",
    "sharedsubpage": "content",
    "dualpane": "content",
    "quiz": "assessment",
    "externalquiz": "assessment",
    "questionnaire": "assessment",
    "forumng": "forum",
    "oucollaborate": "collaboration",
    "ouelluminate": "collaboration",
    "ouwiki": "collaboration",
    "glossary": "other",
    "dataplus": "other",
    "repeatactivity": "other",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def learner_id(raw_id: str) -> str:
    return f"oulad:{raw_id}"


def presentation_id(module: str, presentation: str) -> str:
    return f"oulad:{module}:{presentation}"


def optional_int(value: str) -> int | None:
    return None if value in MISSING else int(value)


def registration_missing_reason(value: str) -> str:
    return "source_missing" if value in MISSING else "observed"


def unregistration_missing_reason(value: str, final_result: str) -> str:
    if value not in MISSING:
        return "observed"
    return "source_missing" if final_result == "Withdrawn" else "not_applicable"


def score_missing_reason(value: str) -> str:
    return "source_missing" if value in MISSING else "observed"


def assessment_date_missing_reason(value: str, assessment_type: str) -> str:
    if value not in MISSING:
        return "observed"
    return "not_supported" if assessment_type == "Exam" else "source_missing"


def activity_group(activity_type: str) -> str:
    try:
        return ACTIVITY_TAXONOMY[activity_type]
    except KeyError as exc:
        raise ValueError(f"unmapped OULAD activity type: {activity_type}") from exc


def enrolment_relation(
    day: int, registration_day: int | None, unregistration_day: int | None
) -> str:
    if registration_day is not None and day < registration_day:
        return "before_registration"
    if unregistration_day is not None and day > unregistration_day:
        return "after_unregistration"
    return "within_known_enrolment"


def course_relation(day: int, course_length: int) -> str:
    if day < 0:
        return "pre_start"
    if day > course_length:
        return "post_course"
    return "in_course"


def due_relation(submitted_day: int, due_day: int | None) -> str:
    if due_day is None:
        return "due_unknown"
    return "on_or_before_due" if submitted_day <= due_day else "late"


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def prepare(data_dir: Path, output_dir: Path, module: str, presentation: str) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            f"output directory is not empty: {output_dir}; choose a new directory"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    pid = presentation_id(module, presentation)

    course_matches = [
        row
        for row in read_rows(data_dir / "courses.csv")
        if row["code_module"] == module and row["code_presentation"] == presentation
    ]
    if len(course_matches) != 1:
        raise ValueError(f"expected one course row for {module}/{presentation}")
    course = course_matches[0]
    course_length = int(course["module_presentation_length"])
    course_rows = [
        {
            "source_id": SOURCE_ID,
            "presentation_id": pid,
            "module_code": module,
            "presentation_code": presentation,
            "length_days": course_length,
            "calendar_start_at": "",
            "calendar_missing_reason": "not_supported",
            "data_origin": "empirical",
        }
    ]

    info_rows = [
        row
        for row in read_rows(data_dir / "studentInfo.csv")
        if row["code_module"] == module and row["code_presentation"] == presentation
    ]
    info_by_student = {row["id_student"]: row for row in info_rows}
    if len(info_by_student) != len(info_rows):
        raise ValueError("duplicate studentInfo enrolment key in selected presentation")

    registration_rows = [
        row
        for row in read_rows(data_dir / "studentRegistration.csv")
        if row["code_module"] == module and row["code_presentation"] == presentation
    ]
    registration_by_student = {row["id_student"]: row for row in registration_rows}
    if set(registration_by_student) != set(info_by_student):
        raise ValueError("studentInfo and studentRegistration learner keys differ")

    enrolments = []
    outcomes = []
    fairness = []
    missingness = Counter()
    for raw_student_id in sorted(info_by_student, key=int):
        info = info_by_student[raw_student_id]
        registration = registration_by_student[raw_student_id]
        reg_reason = registration_missing_reason(registration["date_registration"])
        unreg_reason = unregistration_missing_reason(
            registration["date_unregistration"], info["final_result"]
        )
        imd_reason = "source_missing" if info["imd_band"] in MISSING else "observed"
        missingness[f"registration_day:{reg_reason}"] += 1
        missingness[f"unregistration_day:{unreg_reason}"] += 1
        missingness[f"imd_band:{imd_reason}"] += 1
        enrolments.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "learner_id": learner_id(raw_student_id),
                "registration_day": ""
                if registration["date_registration"] in MISSING
                else registration["date_registration"],
                "registration_missing_reason": reg_reason,
                "unregistration_day": ""
                if registration["date_unregistration"] in MISSING
                else registration["date_unregistration"],
                "unregistration_missing_reason": unreg_reason,
                "previous_attempts": info["num_of_prev_attempts"],
                "studied_credits": info["studied_credits"],
                "data_origin": "empirical",
                "source_record_id": f"{module}/{presentation}/{raw_student_id}",
            }
        )
        outcomes.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "learner_id": learner_id(raw_student_id),
                "final_result": info["final_result"],
                "non_success": int(info["final_result"] in {"Fail", "Withdrawn"}),
                "availability_policy": "course_end_only",
                "restricted_from_predictor": 1,
                "data_origin": "empirical",
            }
        )
        fairness.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "learner_id": learner_id(raw_student_id),
                "gender": info["gender"],
                "region": info["region"],
                "highest_education": info["highest_education"],
                "imd_band": "" if info["imd_band"] in MISSING else info["imd_band"],
                "imd_band_missing_reason": imd_reason,
                "age_band": info["age_band"],
                "disability": info["disability"],
                "restricted_from_predictor": 1,
                "data_origin": "empirical",
            }
        )

    resource_rows = [
        row
        for row in read_rows(data_dir / "vle.csv")
        if row["code_module"] == module and row["code_presentation"] == presentation
    ]
    resources = {}
    prepared_resources = []
    for row in resource_rows:
        group = activity_group(row["activity_type"])
        resources[row["id_site"]] = group
        week_from_reason = "source_missing" if row["week_from"] in MISSING else "observed"
        week_to_reason = "source_missing" if row["week_to"] in MISSING else "observed"
        missingness[f"resource_week_from:{week_from_reason}"] += 1
        missingness[f"resource_week_to:{week_to_reason}"] += 1
        prepared_resources.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "resource_id": f"oulad-site:{row['id_site']}",
                "source_site_id": row["id_site"],
                "activity_type": row["activity_type"],
                "activity_group": group,
                "week_from": "" if row["week_from"] in MISSING else row["week_from"],
                "week_from_missing_reason": week_from_reason,
                "week_to": "" if row["week_to"] in MISSING else row["week_to"],
                "week_to_missing_reason": week_to_reason,
                "data_origin": "empirical",
            }
        )

    raw_assessments = [
        row
        for row in read_rows(data_dir / "assessments.csv")
        if row["code_module"] == module and row["code_presentation"] == presentation
    ]
    assessments_by_id = {row["id_assessment"]: row for row in raw_assessments}
    prepared_assessments = []
    for row in raw_assessments:
        date_reason = assessment_date_missing_reason(row["date"], row["assessment_type"])
        missingness[f"assessment_due_day:{date_reason}"] += 1
        prepared_assessments.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "assessment_id": f"oulad-assessment:{row['id_assessment']}",
                "source_assessment_id": row["id_assessment"],
                "assessment_type": row["assessment_type"],
                "due_course_day": "" if row["date"] in MISSING else row["date"],
                "due_day_missing_reason": date_reason,
                "weight": row["weight"],
                "included_in_checkpoint_features": int(row["assessment_type"] != "Exam"),
                "data_origin": "empirical",
            }
        )

    assessment_observations = []
    learners_with_assessment = set()
    for row in read_rows(data_dir / "studentAssessment.csv"):
        if row["id_assessment"] not in assessments_by_id:
            continue
        raw_student_id = row["id_student"]
        if raw_student_id not in info_by_student:
            raise ValueError(f"assessment row has unknown learner {raw_student_id}")
        score_reason = score_missing_reason(row["score"])
        registration = registration_by_student[raw_student_id]
        registration_day = optional_int(registration["date_registration"])
        unregistration_day = optional_int(registration["date_unregistration"])
        submitted_day = int(row["date_submitted"])
        due_day = optional_int(assessments_by_id[row["id_assessment"]]["date"])
        missingness[f"assessment_score:{score_reason}"] += 1
        learners_with_assessment.add(raw_student_id)
        assessment_observations.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "learner_id": learner_id(raw_student_id),
                "assessment_id": f"oulad-assessment:{row['id_assessment']}",
                "submitted_course_day": submitted_day,
                "course_relation": course_relation(submitted_day, course_length),
                "enrolment_relation": enrolment_relation(
                    submitted_day, registration_day, unregistration_day
                ),
                "due_relation": due_relation(submitted_day, due_day),
                "is_banked": row["is_banked"],
                "score": "" if row["score"] in MISSING else row["score"],
                "score_missing_reason": score_reason,
                "time_precision": "relative_day",
                "data_origin": "empirical",
                "source_record_id": f"{row['id_assessment']}/{raw_student_id}",
            }
        )

    # OULAD contains repeated rows at learner/site/day grain. Aggregate rather
    # than dropping them as duplicates. The selected demo presentation is small
    # enough to aggregate exactly in memory.
    activity_aggregate: dict[tuple[str, str, int], list[int]] = defaultdict(lambda: [0, 0])
    total_activity_source_rows = 0
    for row in read_rows(data_dir / "studentVle.csv"):
        if row["code_module"] != module or row["code_presentation"] != presentation:
            continue
        raw_student_id = row["id_student"]
        if raw_student_id not in info_by_student:
            raise ValueError(f"activity row has unknown learner {raw_student_id}")
        if row["id_site"] not in resources:
            raise ValueError(f"activity row has unknown resource {row['id_site']}")
        total_activity_source_rows += 1
        aggregate = activity_aggregate[(raw_student_id, row["id_site"], int(row["date"]))]
        aggregate[0] += int(row["sum_click"])
        aggregate[1] += 1

    activity_observations = []
    learners_with_activity = set()
    for (raw_student_id, site_id, course_day), (clicks, raw_rows) in sorted(
        activity_aggregate.items(), key=lambda item: (int(item[0][0]), item[0][2], int(item[0][1]))
    ):
        learners_with_activity.add(raw_student_id)
        registration = registration_by_student[raw_student_id]
        registration_day = optional_int(registration["date_registration"])
        unregistration_day = optional_int(registration["date_unregistration"])
        activity_observations.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "learner_id": learner_id(raw_student_id),
                "resource_id": f"oulad-site:{site_id}",
                "course_day": course_day,
                "course_relation": course_relation(course_day, course_length),
                "enrolment_relation": enrolment_relation(
                    course_day, registration_day, unregistration_day
                ),
                "click_count": clicks,
                "raw_row_count": raw_rows,
                "activity_group": resources[site_id],
                "time_precision": "relative_day",
                "data_origin": "empirical",
                "source_record_id": (
                    f"{module}/{presentation}/{raw_student_id}/{site_id}/{course_day}"
                ),
            }
        )

    coverage = []
    for raw_student_id in sorted(info_by_student, key=int):
        has_activity = raw_student_id in learners_with_activity
        has_assessment = raw_student_id in learners_with_assessment
        coverage.append(
            {
                "source_id": SOURCE_ID,
                "presentation_id": pid,
                "learner_id": learner_id(raw_student_id),
                "activity_source_complete": 1,
                "has_activity_rows": int(has_activity),
                "activity_absence_interpretation": "observed"
                if has_activity
                else "structural_zero",
                "has_assessment_rows": int(has_assessment),
                "assessment_absence_interpretation": "evaluate_against_due_dates",
                "data_origin": "empirical",
            }
        )

    outputs = {
        "course_presentations.csv": (course_rows, list(course_rows[0])),
        "enrolments.csv": (enrolments, list(enrolments[0])),
        "outcomes_restricted.csv": (outcomes, list(outcomes[0])),
        "fairness_attributes_restricted.csv": (fairness, list(fairness[0])),
        "resources.csv": (prepared_resources, list(prepared_resources[0])),
        "assessments.csv": (prepared_assessments, list(prepared_assessments[0])),
        "assessment_observations.csv": (
            assessment_observations,
            list(assessment_observations[0]),
        ),
        "activity_observations.csv": (activity_observations, list(activity_observations[0])),
        "enrolment_coverage.csv": (coverage, list(coverage[0])),
    }
    for filename, (rows, fields) in outputs.items():
        write_csv(output_dir / filename, fields, rows)

    replay_calendar = {
        "schema_version": "oulad-replay-calendar-v1",
        "source_presentation_id": pid,
        "synthetic_course_start_at": "2030-01-01T00:00:00+00:00",
        "mapping_rule": "event_at = synthetic_course_start_at + course_day; keep day precision",
        "data_origin": "replayed",
        "generation_method": "fixed-demo-calendar-v1",
        "warning": (
            "This is not the historical OULAD calendar and must not enter "
            "empirical evaluation."
        ),
    }
    (output_dir / "replay_calendar.json").write_text(
        json.dumps(replay_calendar, indent=2), encoding="utf-8"
    )
    (output_dir / "missingness_summary.json").write_text(
        json.dumps(dict(sorted(missingness.items())), indent=2), encoding="utf-8"
    )

    output_manifest = {}
    for path in sorted(output_dir.iterdir()):
        if path.name == "manifest.json":
            continue
        output_manifest[path.name] = {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
    manifest = {
        "schema_version": "oulad-preparation-manifest-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_id": SOURCE_ID,
        "module": module,
        "presentation": presentation,
        "presentation_id": pid,
        "data_origin": "empirical",
        "counts": {
            "enrolments": len(enrolments),
            "resources": len(prepared_resources),
            "assessments": len(prepared_assessments),
            "assessment_observations": len(assessment_observations),
            "activity_source_rows": total_activity_source_rows,
            "activity_aggregated_rows": len(activity_observations),
            "learners_without_activity": len(set(info_by_student) - learners_with_activity),
            "learners_without_assessment_rows": len(
                set(info_by_student) - learners_with_assessment
            ),
        },
        "policies": {
            "raw_source_mutated": False,
            "score_imputation": "none",
            "registration_imputation": "none",
            "resource_schedule_imputation": "none",
            "missing_activity": "structural_zero only because selected source load is complete",
            "missing_assessment": "derived later only after due date and eligibility checks",
            "calendar_synthesis": "separate replay_calendar.json only",
            "time_of_day_synthesis": "none",
            "demographics": "restricted fairness file; excluded from predictor",
            "outcomes": "restricted file; never joined before checkpoint state is frozen",
        },
        "outputs": output_manifest,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("OULAD"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/oulad_demo_v1"))
    parser.add_argument("--module", default="AAA")
    parser.add_argument("--presentation", default="2013J")
    args = parser.parse_args()
    manifest = prepare(
        args.data_dir.resolve(),
        args.output_dir.resolve(),
        args.module,
        args.presentation,
    )
    print("OULAD PREPARATION: PASS")
    print(json.dumps(manifest["counts"], indent=2))
    print(f"output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
