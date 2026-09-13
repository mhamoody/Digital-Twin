"""Reproducible, fictional learning histories; never repairs empirical OULAD rows.

The private scenario oracle is deliberately separate from the exported learning
events and model snapshots. Scenario labels are not predictive evidence.
"""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from digital_twin.workspace.contracts import CaseUpdate, CoursePolicy, digest

GENERATOR_VERSION = "synthetic-education-v1"
SCENARIOS = (
    "steady_success",
    "active_but_low_grades",
    "quiet_but_strong_grades",
    "declining_grades",
    "missed_major_work",
    "approved_extension",
    "awaiting_feedback",
    "recovery_after_support",
    "persistent_difficulty",
    "deadline_pressure",
    "mixed_academic_evidence",
    "interrupted_activity",
)
COURSE_PROFILES = (
    ("CS110", "Foundations of Computing", "weekly", 7, 4),
    ("DS210", "Applied Data Project", "project", 14, 2),
    ("ED220", "Learning and Research Methods", "blended", 10, 3),
)
TOPICS = {
    "CS110": [
        "variables",
        "types",
        "conditions",
        "loops",
        "functions",
        "collections",
        "files",
        "review",
        "testing",
        "debugging",
        "algorithms",
        "search",
        "sorting",
        "modules",
        "integration",
        "revision",
    ],
    "DS210": [
        "research questions",
        "data sources",
        "data quality",
        "exploration",
        "visualisation",
        "sampling",
        "project design",
        "review",
        "validation",
        "model comparison",
        "interpretation",
        "reproducibility",
        "limitations",
        "reporting",
        "project integration",
        "presentation",
    ],
    "ED220": [
        "learning goals",
        "reading strategies",
        "academic sources",
        "note taking",
        "research design",
        "evidence",
        "critical reading",
        "review",
        "argument",
        "peer feedback",
        "revision",
        "citation",
        "reflection",
        "synthesis",
        "communication",
        "presentation",
    ],
}


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _rng(seed: int, *parts: object) -> random.Random:
    key = ":".join(str(part) for part in (GENERATOR_VERSION, seed, *parts))
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def _course(profile: tuple, weeks: int, start: datetime) -> dict[str, Any]:
    code, title, cadence, inactivity_days, expected_days = profile
    presentation_id = f"synthetic:{code}:2026A"
    course = {
        "presentation_id": presentation_id,
        "code": code,
        "title": title,
        "data_origin": "synthetic",
        "start_at": _iso(start),
        "start_date": start.date().isoformat(),
        "end_at": _iso(start + timedelta(weeks=weeks)),
        "timezone": "UTC",
        "weeks": weeks,
        "pass_mark": 50.0,
        "grade_scale_max": 100.0,
        "policy": CoursePolicy(
            inactivity_warning_days=inactivity_days,
            inactivity_high_days=inactivity_days * 2,
            break_ranges=[(49, 55)] if weeks >= 8 else [],
        ).model_dump(mode="json"),
        "calendar": {
            "cadence": cadence,
            "break_weeks": [8] if weeks >= 8 else [],
            "expected_active_days_per_week": expected_days,
            "attendance_supported": cadence == "blended",
        },
        "resources": [],
        "assessments": [],
    }
    for week in range(1, weeks + 1):
        topic = TOPICS[code][(week - 1) % len(TOPICS[code])]
        for kind in ("reading", "worked_example", "practice"):
            resource_id = f"{presentation_id}:resource:w{week}:{kind}"
            course["resources"].append(
                {
                    "resource_id": resource_id,
                    "title": f"{topic.title()}: {kind.replace('_', ' ')}",
                    "topic_ids": [f"{code}:topic:{week}"],
                    "kind": kind,
                    "available_at": _iso(start),
                    "available_day": 0,
                    "week": week,
                    "uri": f"local-resource:{resource_id}",
                    "approved": True,
                    "content": (
                        f"Fictional course resource for {topic}. Work through a short "
                        "example, explain each step, then attempt the practice questions. "
                        "Bring any unresolved step to the next instructor check-in."
                    ),
                }
            )
    assessment_rows: list[tuple[int, str, float]] = []
    for week in range(1, weeks + 1):
        if week in course["calendar"]["break_weeks"]:
            continue
        if cadence == "weekly":
            assessment_rows.append((week, "quiz", 2.0))
            if week % 4 == 0 or week == weeks:
                assessment_rows.append((week, "assignment", 10.0))
        elif cadence == "project":
            assessment_rows.append((week, "practice_quiz", 0.0))
            if week % 2 == 0 or week == weeks:
                assessment_rows.append((week, "project_milestone", 10.0))
        elif week % 2 == 0 or week == weeks:
            assessment_rows.append((week, "quiz", 5.0))
        if cadence == "blended" and (week % 5 == 0 or week == weeks):
            assessment_rows.append((week, "portfolio", 15.0))
    if not assessment_rows:
        assessment_rows.append((weeks, "assignment", 10.0))
    total_weight = sum(row[2] for row in assessment_rows)
    for ordinal, (week, kind, weight) in enumerate(assessment_rows, 1):
        course["assessments"].append(
            {
                "assessment_id": f"{presentation_id}:assessment:{ordinal:03d}",
                "title": f"Week {week} {kind.replace('_', ' ')}",
                "kind": kind,
                "week": week,
                "topic_ids": [f"{code}:topic:{week}"],
                "available_at": _iso(start),
                "available_day": 0,
                "due_day": week * 7 - 1,
                "due_at": _iso(start + timedelta(days=week * 7 - 1, hours=17)),
                "max_score": 100.0,
                "weight": round(weight / total_weight * 100, 8),
                "required": weight > 0,
            }
        )
    return course


def _trajectory(scenario: str, week: int, base_grade: float) -> tuple[float, float]:
    """Joint engagement and academic trajectories, not labels copied from a risk rule."""
    activity, grade = 0.65, base_grade
    if scenario == "active_but_low_grades":
        activity, grade = 0.9, 39 + week * 0.4
    elif scenario == "quiet_but_strong_grades":
        activity, grade = 0.22, 87
    elif scenario == "declining_grades":
        activity, grade = max(0.15, 0.85 - week * 0.04), 88 - week * 3.3
    elif scenario == "missed_major_work":
        activity, grade = 0.45, 61
    elif scenario == "recovery_after_support":
        activity, grade = (0.2, 43) if week <= 6 else (0.75, min(85, 52 + 3 * (week - 6)))
    elif scenario == "persistent_difficulty":
        activity, grade = 0.5, 37
    elif scenario == "deadline_pressure":
        activity, grade = 0.3, 57
    elif scenario == "mixed_academic_evidence":
        activity, grade = 0.8, 85 if week % 2 else 38
    elif scenario == "interrupted_activity":
        activity, grade = (0.0, 55) if 6 <= week <= 10 else (0.68, 75)
    return activity, grade


def _learner_events(course: dict, enrolment: dict, scenario: str, seed: int) -> list[dict]:
    randomizer = _rng(seed, course["presentation_id"], enrolment["learner_id"])
    start = datetime.fromisoformat(course["start_at"])
    weeks = course["weeks"]
    base_grade = randomizer.uniform(68, 88)
    events: list[dict] = []

    def emit(kind: str, occurred: datetime, payload: dict, available: datetime | None = None):
        event_id = f"{enrolment['learner_id']}:{course['code']}:e{len(events):05d}"
        events.append(
            {
                "event_id": event_id,
                "source_record_id": event_id,
                "presentation_id": course["presentation_id"],
                "learner_id": enrolment["learner_id"],
                "event_type": kind,
                "occurred_at": _iso(occurred),
                "available_at": _iso(available or occurred),
                "course_day": (occurred.date() - start.date()).days,
                "available_day": ((available or occurred).date() - start.date()).days,
                "data_origin": "synthetic",
                "time_precision": "exact",
                "payload": payload,
            }
        )

    emit("enrolment", datetime.fromisoformat(enrolment["registered_at"]), {"status": "active"})
    for day in range(weeks * 7):
        week = day // 7 + 1
        activity, _grade = _trajectory(scenario, week, base_grade)
        if week in course["calendar"]["break_weeks"]:
            activity *= 0.12
        if course["calendar"]["cadence"] == "project":
            activity *= 0.7 if day % 7 < 3 else 1.05
        occurred = start + timedelta(
            days=day, hours=randomizer.randint(8, 21), minutes=randomizer.randint(0, 59)
        )
        if randomizer.random() < activity:
            resources = [r for r in course["resources"] if r["week"] == week]
            resource = randomizer.choice(resources)
            emit(
                "activity",
                occurred,
                {
                    "resource_id": resource["resource_id"],
                    "topic_ids": resource["topic_ids"],
                    "count": randomizer.randint(2, 24),
                    "duration_minutes": randomizer.randint(8, 75),
                    "duration_measurement": "simulated_session",
                    "kind": resource["kind"],
                },
            )
            if randomizer.random() < 0.55:
                emit(
                    "resource_completed",
                    occurred + timedelta(minutes=2),
                    {
                        "resource_id": resource["resource_id"],
                        "topic_ids": resource["topic_ids"],
                    },
                )
            if randomizer.random() < 0.08:
                topic = TOPICS[course["code"]][(week - 1) % 16]
                text = (
                    f"I attempted the {topic} practice but cannot explain the last step. "
                    "Could we review another example before the next task?"
                )
                if scenario in {"steady_success", "quiet_but_strong_grades"}:
                    text = (
                        f"I completed the {topic} practice. Comparing the worked example "
                        "with my answer helped me explain the steps."
                    )
                emit(
                    "forum_post",
                    occurred + timedelta(minutes=3),
                    {
                        "text": text,
                        "topic_ids": resource["topic_ids"],
                        "thread_id": f"{course['code']}:forum:w{week}",
                    },
                )
        if (
            course["calendar"]["attendance_supported"]
            and day % 7 in (1, 3)
            and week not in course["calendar"]["break_weeks"]
        ):
            emit(
                "attendance",
                start + timedelta(days=day, hours=11),
                {
                    "session_id": f"{course['code']}:session:{day}",
                    "present": randomizer.random()
                    < (0.63 if scenario == "persistent_difficulty" else 0.9),
                },
            )

    for assessment in course["assessments"]:
        week = assessment["week"]
        _activity, mean_grade = _trajectory(scenario, week, base_grade)
        due = datetime.fromisoformat(assessment["due_at"])
        effective_due = due
        if scenario == "approved_extension" and week % 4 == 0:
            effective_due += timedelta(days=7)
            emit(
                "assessment_extension",
                due - timedelta(days=3),
                {
                    "assessment_id": assessment["assessment_id"],
                    "extended_due_at": _iso(effective_due),
                    "status": "approved",
                    "extended_due_day": (effective_due.date() - start.date()).days,
                },
            )
        missed = (
            (scenario == "missed_major_work" and assessment["kind"] != "quiz" and week >= 4)
            or (scenario == "persistent_difficulty" and week % 3 == 0)
            or (scenario == "interrupted_activity" and 6 <= week <= 10)
        )
        if missed:
            continue
        submission = effective_due + timedelta(hours=randomizer.choice((-48, -24, -6, 0, 6)))
        if scenario == "deadline_pressure":
            submission = effective_due + timedelta(days=randomizer.choice((0, 1, 2)))
        if scenario == "approved_extension" and effective_due != due:
            submission = due + timedelta(days=4)
        emit(
            "assessment_submission",
            submission,
            {
                "assessment_id": assessment["assessment_id"],
                "attempt": 1,
                "topic_ids": assessment["topic_ids"],
            },
        )
        grade = round(min(100, max(0, randomizer.gauss(mean_grade, 8))), 1)
        is_quiz = assessment["kind"] in {"quiz", "practice_quiz"}
        publication = submission + timedelta(hours=1 if is_quiz else randomizer.randint(48, 120))
        if scenario == "awaiting_feedback" and not is_quiz:
            publication = submission + timedelta(days=12)
        emit(
            "assessment_grade",
            submission,
            {
                "assessment_id": assessment["assessment_id"],
                "attempt": 1,
                "score": grade,
                "max_score": assessment["max_score"],
                "topic_ids": assessment["topic_ids"],
                "published_at": _iso(publication),
                "feedback": (
                    "Review the worked example and explain the steps in your next attempt."
                    if grade < 55
                    else "The submitted work meets the assessed criteria."
                ),
            },
            publication,
        )
    if scenario in {"recovery_after_support", "persistent_difficulty"} and weeks >= 6:
        resource = next(r for r in course["resources"] if r["week"] == 6)
        emit(
            "intervention",
            start + timedelta(days=39, hours=12),
            {
                "action_type": "support_provided",
                "recorded_by": "synthetic:instructor",
                "note": "Discussed recent submitted work and provided a worked example.",
                "resource_ids": [resource["resource_id"]],
                "follow_up_at": _iso(start + timedelta(days=53, hours=12)),
                "follow_up_day": 53,
                "status": "ongoing",
            },
        )
        if weeks >= 8:
            emit(
                "follow_up",
                start + timedelta(days=53, hours=12),
                {
                    "action_type": "follow_up",
                    "recorded_by": "synthetic:instructor",
                    "note": "Reviewed the new submission and asked about remaining questions.",
                    "status": "ongoing",
                },
            )
    return sorted(events, key=lambda event: (event["occurred_at"], event["event_id"]))


def generate_dataset(
    seed: int = 2026, learners_per_course: int = 120, weeks: int = 16
) -> dict[str, Any]:
    """Create a complete applicable-data cohort and paired degraded snapshots.

    No database, filesystem or network writes occur here. The caller owns storage.
    """
    if not 1 <= learners_per_course <= 2000 or not 2 <= weeks <= 52:
        raise ValueError("Use 1..2000 learners per course and 2..52 course weeks")
    from digital_twin.workspace.features import build_snapshot

    start = datetime(2026, 1, 5, tzinfo=UTC)
    courses = [_course(profile, weeks, start) for profile in COURSE_PROFILES]
    enrolments: list[dict] = []
    events: list[dict] = []
    snapshots: list[dict] = []
    oracle: list[dict] = []
    for course_index, course in enumerate(courses):
        for index in range(learners_per_course):
            learner_id = f"synthetic:learner:{course_index + 1}:{index + 1:04d}"
            scenario = SCENARIOS[index % len(SCENARIOS)]
            enrolment = {
                "presentation_id": course["presentation_id"],
                "learner_id": learner_id,
                "display_name": f"Demo learner {course_index + 1}-{index + 1:03d}",
                "registered_at": _iso(start - timedelta(days=7 + index % 14)),
                "registration_day": -7 - index % 14,
                "unregistration_day": None,
                "status": "active",
                "data_origin": "synthetic",
            }
            enrolments.append(enrolment)
            learner_events = _learner_events(course, enrolment, scenario, seed)
            events.extend(learner_events)
            for week in range(1, weeks + 1):
                snapshots.append(build_snapshot(course, enrolment, learner_events, week))
            oracle.append(
                {
                    "presentation_id": course["presentation_id"],
                    "learner_id": learner_id,
                    "trajectory": scenario,
                    "purpose": "Scenario assertions only; not empirical outcome ground truth",
                }
            )
    return {
        "manifest": {
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
            "data_origin": "synthetic",
            "learners_per_course": learners_per_course,
            "weeks": weeks,
            "course_count": len(courses),
            "enrolment_count": len(enrolments),
            "event_count": len(events),
            "snapshot_count": len(snapshots),
            "empirical_data_modified": False,
            "purpose": "Fictional scenario coverage and integration testing, not measured accuracy",
        },
        "courses": courses,
        "enrolments": enrolments,
        "events": events,
        "snapshots": snapshots,
        "oracle": oracle,
    }


def seed_support_history(store: Any, dataset: dict[str, Any]) -> dict[str, int]:
    """Import only generated completed support actions with repeat-safe identities.

    Call after ``Store.ingest_dataset``. Cases appear only at or after their
    recorded course day when read through a historical checkpoint. Existing
    independently edited cases are protected by the store's optimistic version
    checks; this helper never deletes history to make a fixture fit.
    """
    grouped: dict[tuple[str, str], list[dict]] = {}
    for event in dataset["events"]:
        if event["event_type"] not in {"intervention", "follow_up"}:
            continue
        if event.get("data_origin") != "synthetic":
            raise ValueError("Seeded support history requires explicitly synthetic records")
        grouped.setdefault((event["presentation_id"], event["learner_id"]), []).append(event)
    count = 0
    for (course_id, learner_id), events in sorted(grouped.items()):
        ordered = sorted(events, key=lambda event: (event["course_day"], event["event_id"]))
        for ordinal, event in enumerate(ordered):
            day = max(event["course_day"], event["available_day"])
            raw = event["payload"]
            change = CaseUpdate(
                status=raw.get("status", "ongoing"),
                expected_version=ordinal,
                note=raw.get("note", ""),
                action="support" if event["event_type"] == "intervention" else "follow_up",
                action_state="completed",
                occurred_day=day,
                follow_up_day=raw.get("follow_up_day"),
                resource_ids=raw.get("resource_ids", []),
                checkpoint_week=day // 7 + 1,
            )
            store.update_case(
                course_id,
                learner_id,
                change,
                actor="system:synthetic-demo",
                request_key=digest(["synthetic-support-v1", event["event_id"]]),
            )
            count += 1
    return {"synthetic_cases": len(grouped), "requested_history_events": count}
