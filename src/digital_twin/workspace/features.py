"""Cutoff-safe academic evidence from source-neutral events and course context."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from digital_twin.workspace.contracts import (
    CoursePolicy,
    EvidenceFact,
    LearnerSnapshot,
    digest,
)

ACTIVITY_FEATURES = {
    "clicks_last_7",
    "active_days_last_7",
    "active_days_last_14",
    "activity_change_last_7",
    "study_minutes_last_7",
    "days_since_last_activity",
    "teaching_days_since_last_activity",
    "resources_completed",
    "completion_percent",
}
GRADE_FEATURES = {
    "grades_available",
    "weighted_grade_percent",
    "latest_grade_percent",
    "grade_change_points",
    "low_grade_count",
    "grade_weight_observed_percent",
    "quiz_average_percent",
    "pending_grade_count",
}


def teaching_days_between(
    last_day: int, cutoff_day: int, start_date: str, policy: CoursePolicy
) -> int:
    """Count days after the last activity, excluding declared nonteaching days."""
    start = datetime.fromisoformat(start_date).date()
    return sum(
        1
        for day in range(last_day + 1, cutoff_day + 1)
        if (start + timedelta(days=day)).weekday() in policy.teaching_weekdays
        and not any(first <= day <= last for first, last in policy.break_ranges)
    )


def _eligible_events(course: dict, enrolment: dict, events: list[dict], cutoff: int) -> list[dict]:
    selected = []
    for event in events:
        if (
            event["presentation_id"] != course["presentation_id"]
            or event["learner_id"] != enrolment["learner_id"]
        ):
            continue
        if int(event["course_day"]) <= cutoff and int(event["available_day"]) <= cutoff:
            selected.append(event)
    return sorted(selected, key=lambda e: (e["available_day"], e["course_day"], e["event_id"]))


def build_snapshot(
    course: dict,
    enrolment: dict,
    events: list[dict],
    checkpoint_week: int,
    *,
    policy: CoursePolicy | None = None,
) -> LearnerSnapshot:
    """Aggregate only events from this enrolment that were available by the cutoff."""
    cutoff = checkpoint_week * 7 - 1
    policy = policy or CoursePolicy.model_validate(course["policy"])
    eligible = _eligible_events(course, enrolment, events, cutoff)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for event in eligible:
        grouped[event["event_type"]].append(event)
    definitions = {
        assessment["assessment_id"]: assessment
        for assessment in course["assessments"]
        if assessment["available_day"] <= cutoff
    }
    extensions = {
        event["payload"]["assessment_id"]: event
        for event in grouped["assessment_extension"]
        if event["payload"].get("status") == "approved"
    }
    due_days = {
        key: int(extensions[key]["payload"]["extended_due_day"])
        if key in extensions
        else int(definition["due_day"])
        for key, definition in definitions.items()
    }
    required = {
        key: definition
        for key, definition in definitions.items()
        if definition.get("required", True)
    }
    due = {key: value for key, value in required.items() if due_days[key] <= cutoff}
    submitted = {
        event["payload"]["assessment_id"]: event for event in grouped["assessment_submission"]
    }
    grades = {
        event["payload"]["assessment_id"]: event
        for event in grouped["assessment_grade"]
        if event["payload"]["assessment_id"] in definitions
    }
    grade_events = sorted(grades.values(), key=lambda e: (e["available_day"], e["event_id"]))
    activity = grouped["activity"]
    recent = [event for event in activity if event["course_day"] > cutoff - 7]
    previous = [event for event in activity if cutoff - 14 < event["course_day"] <= cutoff - 7]
    recent14 = [event for event in activity if event["course_day"] > cutoff - 14]
    facts: dict[str, EvidenceFact] = {}
    identity = digest(
        {
            "course": course["presentation_id"],
            "learner": enrolment["learner_id"],
            "week": checkpoint_week,
            "policy": policy.model_dump(mode="json"),
            "events": eligible,
            "assessments": definitions,
            "resources": course["resources"],
            "calendar": course["calendar"],
        }
    )[:24]

    def fact(
        name: str,
        value: Any,
        sources: list[dict] | None = None,
        *,
        unit: str = "count",
        window: str = "through checkpoint",
        status: str | None = None,
        definition_ids: list[str] | None = None,
    ):
        sources = sources or []
        available_days = [int(event["available_day"]) for event in sources]
        facts[name] = EvidenceFact(
            evidence_id=f"synthetic:ev:{identity}:{name}",
            value=value,
            status=status
            or (
                "not_yet_applicable"
                if value is None
                else "structural_zero"
                if value == 0 and not sources
                else "observed"
            ),
            unit=unit,
            window=window,
            source_ids=[event["event_id"] for event in sources] + (definition_ids or []),
            available_day=max(available_days, default=0),
        )

    fact(
        "clicks_last_7",
        sum(event["payload"]["count"] for event in recent),
        recent,
        window="last 7 calendar days",
    )
    fact(
        "active_days_last_7",
        len({event["course_day"] for event in recent}),
        recent,
        unit="days",
        window="last 7 calendar days",
    )
    fact(
        "active_days_last_14",
        len({event["course_day"] for event in recent14}),
        recent14,
        unit="days",
        window="last 14 calendar days",
    )
    fact(
        "activity_change_last_7",
        sum(event["payload"]["count"] for event in recent)
        - sum(event["payload"]["count"] for event in previous),
        recent + previous,
        window="last 7 days minus preceding 7 days",
    )
    fact(
        "study_minutes_last_7",
        sum(event["payload"].get("duration_minutes", 0) for event in recent),
        recent,
        unit="simulated minutes",
        window="last 7 calendar days",
    )
    if activity:
        last = max(activity, key=lambda event: event["course_day"])
        fact("days_since_last_activity", cutoff - last["course_day"], [last], unit="days")
        fact(
            "teaching_days_since_last_activity",
            teaching_days_between(last["course_day"], cutoff, course["start_date"], policy),
            [last],
            unit="teaching days",
        )
    else:
        fact("days_since_last_activity", None, status="no_activity_yet", unit="days")
        fact(
            "teaching_days_since_last_activity",
            None,
            status="no_activity_yet",
            unit="teaching days",
        )

    expected_resources = {
        resource["resource_id"]
        for resource in course["resources"]
        if resource["week"] <= checkpoint_week
        and resource["available_day"] <= cutoff
        and resource["week"] not in course["calendar"]["break_weeks"]
    }
    completed = {event["payload"]["resource_id"] for event in grouped["resource_completed"]}
    fact("resources_completed", len(completed & expected_resources), grouped["resource_completed"])
    fact("resources_expected", len(expected_resources), definition_ids=sorted(expected_resources))
    fact(
        "completion_percent",
        round(100 * len(completed & expected_resources) / len(expected_resources), 1)
        if expected_resources
        else None,
        grouped["resource_completed"],
        unit="percent",
        definition_ids=sorted(expected_resources),
    )
    due_submissions = [submitted[key] for key in due if key in submitted]
    missed = [key for key in due if key not in submitted]
    late = [
        submitted[key]
        for key in due
        if key in submitted and submitted[key]["course_day"] > due_days[key]
    ]
    fact("assessments_due", len(due), definition_ids=list(due))
    fact("assessments_submitted", len(due_submissions), due_submissions)
    fact("assessments_missed", len(missed), definition_ids=missed)
    fact("assessments_late", len(late), late)
    fact(
        "submission_rate_percent",
        round(100 * len(due_submissions) / len(due), 1) if due else None,
        due_submissions,
        unit="percent",
        definition_ids=list(due),
    )

    def grade_percent(event: dict) -> float:
        return event["payload"]["score"] / event["payload"]["max_score"] * 100

    weighted = [
        (event, definitions[event["payload"]["assessment_id"]]["weight"])
        for event in grade_events
        if definitions[event["payload"]["assessment_id"]]["weight"] > 0
    ]
    observed_weight = sum(weight for _event, weight in weighted)
    fact("grades_available", len(grade_events), grade_events)
    fact(
        "weighted_grade_percent",
        round(sum(grade_percent(event) * weight for event, weight in weighted) / observed_weight, 1)
        if observed_weight
        else None,
        grade_events,
        unit="percent",
    )
    fact(
        "latest_grade_percent",
        grade_percent(grade_events[-1]) if grade_events else None,
        grade_events[-1:],
        unit="percent",
    )
    change = (
        sum(grade_percent(event) for event in grade_events[-2:]) / 2
        - sum(grade_percent(event) for event in grade_events[-4:-2]) / 2
    )
    fact(
        "grade_change_points",
        round(change, 1) if len(grade_events) >= 4 else None,
        grade_events[-4:],
        unit="percentage points",
        window="latest 2 minus preceding 2 published grades",
    )
    fact(
        "low_grade_count",
        sum(grade_percent(event) < policy.low_grade_percent for event in grade_events),
        grade_events,
    )
    fact("grade_weight_observed_percent", round(observed_weight, 2), grade_events, unit="percent")
    pending = [
        event for key, event in submitted.items() if key not in grades and key in definitions
    ]
    fact("pending_grade_count", len(pending), pending)
    quizzes = [
        event
        for event in grade_events
        if definitions[event["payload"]["assessment_id"]]["kind"] in {"quiz", "practice_quiz"}
    ]
    fact(
        "quiz_average_percent",
        round(sum(grade_percent(event) for event in quizzes) / len(quizzes), 1)
        if quizzes
        else None,
        quizzes,
        unit="percent",
    )
    upcoming = [
        definition
        for key, definition in required.items()
        if cutoff < due_days[key] <= cutoff + 7 and key not in submitted
    ]
    next_days = [
        due_days[key] - cutoff
        for key in required
        if due_days[key] > cutoff and key not in submitted
    ]
    fact(
        "upcoming_assessments_7d",
        len(upcoming),
        definition_ids=[d["assessment_id"] for d in upcoming],
        window="next 7 days; schedule known by checkpoint",
    )
    fact(
        "upcoming_weight_7d",
        round(sum(item["weight"] for item in upcoming), 2),
        unit="percent",
        definition_ids=[d["assessment_id"] for d in upcoming],
        window="next 7 days",
    )
    fact(
        "days_to_next_deadline",
        min(next_days) if next_days else None,
        unit="days",
        definition_ids=list(required),
    )
    active_extensions = [
        event for key, event in extensions.items() if key in due_days and due_days[key] > cutoff
    ]
    fact("extensions_active", len(active_extensions), active_extensions)
    attendance = grouped["attendance"]
    if course["calendar"]["attendance_supported"]:
        fact("attendance_sessions", len(attendance), attendance)
        fact(
            "attendance_rate_percent",
            round(
                100 * sum(event["payload"]["present"] for event in attendance) / len(attendance), 1
            )
            if attendance
            else None,
            attendance,
            unit="percent",
        )
    else:
        fact("attendance_sessions", None, status="not_supported")
        fact("attendance_rate_percent", None, status="not_supported", unit="percent")
    posts = [event for event in grouped["forum_post"] if event["course_day"] > cutoff - 14]
    fact("forum_posts_last_14", len(posts), posts, window="last 14 calendar days")
    fact(
        "latest_forum_excerpt",
        posts[-1]["payload"]["text"][:800] if posts else None,
        posts[-1:],
        unit="text",
        window="latest post in last 14 calendar days",
    )
    interventions = grouped["intervention"] + grouped["follow_up"]
    fact("intervention_count", len(interventions), interventions)
    fact(
        "last_intervention_day",
        max(event["course_day"] for event in interventions) if interventions else None,
        interventions,
        unit="course day",
    )
    weak_topics = {
        topic
        for event in grade_events
        if grade_percent(event) < policy.low_grade_percent
        for topic in event["payload"].get("topic_ids", [])
    }
    relevant_resources = [
        resource
        for resource in course["resources"]
        if resource["available_day"] <= cutoff
        and (resource["week"] == checkpoint_week or weak_topics.intersection(resource["topic_ids"]))
    ]
    context = {
        "course_title": course["title"],
        "course_start_date": course["start_date"],
        "course_week": checkpoint_week,
        "weeks_total": course["weeks"],
        "pass_mark": course["pass_mark"],
        "policy": policy.model_dump(mode="json"),
        "calendar": course["calendar"],
        "is_break_week": checkpoint_week in course["calendar"]["break_weeks"],
        "resources": relevant_resources[-9:],
        "upcoming_assessments": [
            dict(item, effective_due_day=due_days[item["assessment_id"]]) for item in upcoming
        ],
        "recent_interventions": [
            dict(event["payload"], occurred_day=event["course_day"]) for event in interventions[-3:]
        ],
        "interpretation": "Simulated data. Study minutes are generated, not measured learner time.",
    }
    return LearnerSnapshot(
        state_id=f"synthetic:state:{identity}",
        presentation_id=course["presentation_id"],
        learner_id=enrolment["learner_id"],
        checkpoint_week=checkpoint_week,
        cutoff_day=cutoff,
        data_origin="synthetic",
        built_at=(
            datetime.fromisoformat(course["start_date"]).replace(tzinfo=UTC)
            + timedelta(days=cutoff, hours=23, minutes=59)
        ).isoformat(),
        coverage={
            "activity": "complete",
            "assessments": "complete",
            "grades": "complete",
            "forum": "complete",
            "attendance": "complete"
            if attendance
            else "not_supported"
            if not course["calendar"]["attendance_supported"]
            else "complete",
        },
        course_context=context,
        features=facts,
    )


def degrade_snapshot(snapshot: LearnerSnapshot, mode: str) -> LearnerSnapshot:
    """Create a paired fault fixture without mutating complete evidence or its source."""
    payload = snapshot.model_dump(mode="json")
    if mode == "missing_grades":
        names, status = GRADE_FEATURES, "source_missing"
        payload["coverage"]["grades"] = "missing"
    elif mode == "partial_activity":
        names, status = ACTIVITY_FEATURES, "ingestion_incomplete"
        payload["coverage"]["activity"] = "partial"
    elif mode == "stale_activity":
        names, status = ACTIVITY_FEATURES, "ingestion_incomplete"
        payload["coverage"]["activity"] = "partial"
        payload["is_fresh"] = False
    else:
        raise ValueError(
            "Unknown degradation; use missing_grades, partial_activity or stale_activity"
        )
    for name in names:
        payload["features"][name].update(value=None, status=status, source_ids=[])
    identity = digest({"base_state": snapshot.state_id, "mode": mode})[:24]
    payload["state_id"] = f"synthetic:state:{identity}"
    for name, feature in payload["features"].items():
        feature["evidence_id"] = f"synthetic:ev:{identity}:{name}"
    # Remove context that was derived from the deliberately unavailable stream.
    if mode == "missing_grades":
        payload["course_context"]["resources"] = [
            resource
            for resource in payload["course_context"]["resources"]
            if resource["week"] == snapshot.checkpoint_week
        ]
    return LearnerSnapshot.model_validate(payload)
