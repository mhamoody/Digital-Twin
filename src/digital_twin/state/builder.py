"""Build versioned weekly states using only observations available by cutoff."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from digital_twin.schemas import DataOrigin, MissingReason, WeeklyFeature, WeeklyState

FEATURE_SET_VERSION = "oulad-demo-features-v1"
ACTIVITY_GROUPS = ("content", "assessment", "forum", "collaboration", "other")


def _hash_strings(values: Iterable[str]) -> str:
    payload = "\n".join(sorted(values)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _feature(
    *,
    state_id: str,
    name: str,
    value: float | int | bool | str | None,
    missing_reason: MissingReason,
    source_ids: Iterable[str],
) -> WeeklyFeature:
    ids = sorted(set(source_ids))
    evidence_id = _bounded_identifier(f"ev:{state_id}:{name}")
    reference = _bounded_identifier(f"prov:{state_id}:{name}")
    # Inline a few identifiers for debugging while retaining complete compact
    # provenance through count + hash.
    inline_ids = ids[:8]
    return WeeklyFeature(
        name=name,
        value=value,
        missing_reason=missing_reason,
        evidence_id=evidence_id,
        source_observation_ids=inline_ids,
        provenance_reference=reference,
        source_observation_count=len(ids),
        source_observation_hash=_hash_strings(ids),
    )


def _bounded_identifier(value: str) -> str:
    if len(value) <= 128:
        return value
    return f"{value.split(':', 1)[0]}:{hashlib.sha256(value.encode()).hexdigest()}"


def calculate_input_hash(state_payload: dict) -> str:
    """Hash only deterministic state identity, values, missingness, and provenance."""

    normalized = json.dumps(state_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _window_rows(activity_rows: list[dict], cutoff: int, days: int | None) -> list[dict]:
    rows = [row for row in activity_rows if int(row["course_day"]) <= cutoff]
    if days is None:
        return rows
    lower = cutoff - days + 1
    return [row for row in rows if int(row["course_day"]) >= lower]


def _activity_feature(
    *,
    state_id: str,
    name: str,
    value: int,
    rows: list[dict],
) -> WeeklyFeature:
    missing = MissingReason.OBSERVED if rows else MissingReason.STRUCTURAL_ZERO
    return _feature(
        state_id=state_id,
        name=name,
        value=value,
        missing_reason=missing,
        source_ids=(row["source_record_id"] for row in rows),
    )


def build_weekly_states(
    *,
    enrolments: list[dict],
    activities: list[dict],
    assessments: list[dict],
    assessment_observations: list[dict],
    checkpoints: tuple[int, ...],
    built_at: datetime,
    data_origin: DataOrigin = DataOrigin.EMPIRICAL,
    feature_set_version: str = FEATURE_SET_VERSION,
    is_fresh: bool = True,
) -> list[WeeklyState]:
    """Build eligible states without joining outcomes or post-cutoff records."""

    activity_by_learner: dict[str, list[dict]] = defaultdict(list)
    for row in activities:
        activity_by_learner[row["learner_id"]].append(row)

    assessment_obs_by_learner: dict[str, list[dict]] = defaultdict(list)
    for row in assessment_observations:
        if row["is_banked"] != "1":
            assessment_obs_by_learner[row["learner_id"]].append(row)

    non_exam_assessments = [
        row for row in assessments if row["included_in_checkpoint_features"] == "1"
    ]
    assessment_by_id = {row["assessment_id"]: row for row in non_exam_assessments}
    states = []

    for enrolment in sorted(enrolments, key=lambda row: row["learner_id"]):
        learner_id = enrolment["learner_id"]
        presentation_id = enrolment["presentation_id"]
        registration_day = (
            None if enrolment["registration_day"] == "" else int(enrolment["registration_day"])
        )
        unregistration_day = (
            None if enrolment["unregistration_day"] == "" else int(enrolment["unregistration_day"])
        )
        learner_activities = activity_by_learner.get(learner_id, [])
        learner_assessments = assessment_obs_by_learner.get(learner_id, [])

        for checkpoint_week in checkpoints:
            cutoff = checkpoint_week * 7 - 1
            if registration_day is not None and registration_day > cutoff:
                continue
            if unregistration_day is not None and unregistration_day <= cutoff:
                continue

            state_id = (
                f"state:{presentation_id}:{learner_id}:w{checkpoint_week}:{feature_set_version}"
            )
            feature_rows: list[WeeklyFeature] = []
            cumulative_rows = _window_rows(learner_activities, cutoff, None)

            for days in (7, 14, 28):
                rows = _window_rows(learner_activities, cutoff, days)
                feature_rows.append(
                    _activity_feature(
                        state_id=state_id,
                        name=f"clicks_last_{days}",
                        value=sum(int(row["click_count"]) for row in rows),
                        rows=rows,
                    )
                )
                feature_rows.append(
                    _activity_feature(
                        state_id=state_id,
                        name=f"active_days_last_{days}",
                        value=len({int(row["course_day"]) for row in rows}),
                        rows=rows,
                    )
                )

            feature_rows.extend(
                [
                    _activity_feature(
                        state_id=state_id,
                        name="clicks_cumulative",
                        value=sum(int(row["click_count"]) for row in cumulative_rows),
                        rows=cumulative_rows,
                    ),
                    _activity_feature(
                        state_id=state_id,
                        name="active_days_cumulative",
                        value=len({int(row["course_day"]) for row in cumulative_rows}),
                        rows=cumulative_rows,
                    ),
                ]
            )

            if cumulative_rows:
                latest_day = max(int(row["course_day"]) for row in cumulative_rows)
                latest_rows = [
                    row for row in cumulative_rows if int(row["course_day"]) == latest_day
                ]
                feature_rows.append(
                    _feature(
                        state_id=state_id,
                        name="days_since_last_activity",
                        value=cutoff - latest_day,
                        missing_reason=MissingReason.OBSERVED,
                        source_ids=(row["source_record_id"] for row in latest_rows),
                    )
                )
            else:
                feature_rows.append(
                    _feature(
                        state_id=state_id,
                        name="days_since_last_activity",
                        value=None,
                        missing_reason=MissingReason.NO_ACTIVITY_YET,
                        source_ids=(),
                    )
                )

            for group in ACTIVITY_GROUPS:
                rows = [row for row in cumulative_rows if row["activity_group"] == group]
                feature_rows.append(
                    _activity_feature(
                        state_id=state_id,
                        name=f"{group}_clicks_cumulative",
                        value=sum(int(row["click_count"]) for row in rows),
                        rows=rows,
                    )
                )

            due_assessments = [
                row
                for row in non_exam_assessments
                if row["due_course_day"] != "" and int(row["due_course_day"]) <= cutoff
            ]
            due_ids = {row["assessment_id"] for row in due_assessments}
            submitted_rows = [
                row
                for row in learner_assessments
                if row["assessment_id"] in due_ids and int(row["submitted_course_day"]) <= cutoff
            ]
            submitted_ids = {row["assessment_id"] for row in submitted_rows}
            missed_ids = due_ids - submitted_ids
            due_source_ids = [
                row.get("source_record_id")
                or f"assessment-definition:{row['source_assessment_id']}"
                for row in due_assessments
            ]
            submitted_source_ids = [row["source_record_id"] for row in submitted_rows]

            due_missing = (
                MissingReason.OBSERVED if due_assessments else MissingReason.NOT_YET_APPLICABLE
            )
            feature_rows.append(
                _feature(
                    state_id=state_id,
                    name="assessments_due",
                    value=len(due_assessments) if due_assessments else None,
                    missing_reason=due_missing,
                    source_ids=due_source_ids,
                )
            )
            feature_rows.append(
                _feature(
                    state_id=state_id,
                    name="assessments_submitted",
                    value=len(submitted_ids) if due_assessments else None,
                    missing_reason=(
                        MissingReason.OBSERVED if submitted_rows else MissingReason.STRUCTURAL_ZERO
                    )
                    if due_assessments
                    else due_missing,
                    source_ids=submitted_source_ids if due_assessments else (),
                )
            )
            feature_rows.append(
                _feature(
                    state_id=state_id,
                    name="assessments_missed",
                    value=len(missed_ids) if due_assessments else None,
                    missing_reason=(
                        MissingReason.OBSERVED if missed_ids else MissingReason.STRUCTURAL_ZERO
                    )
                    if due_assessments
                    else due_missing,
                    source_ids=(
                        assessment_by_id[item].get("source_record_id")
                        or (
                            "assessment-definition:"
                            f"{assessment_by_id[item]['source_assessment_id']}"
                        )
                        for item in sorted(missed_ids)
                    )
                    if due_assessments
                    else (),
                )
            )
            feature_rows.append(
                _feature(
                    state_id=state_id,
                    name="submission_rate",
                    value=(len(submitted_ids) / len(due_ids)) if due_ids else None,
                    missing_reason=due_missing,
                    source_ids=(*due_source_ids, *submitted_source_ids) if due_ids else (),
                )
            )

            enrolment_source = [enrolment["source_record_id"]]
            feature_rows.append(
                _feature(
                    state_id=state_id,
                    name="previous_attempts",
                    value=int(enrolment["previous_attempts"]),
                    missing_reason=MissingReason.OBSERVED,
                    source_ids=enrolment_source,
                )
            )
            feature_rows.append(
                _feature(
                    state_id=state_id,
                    name="studied_credits",
                    value=int(enrolment["studied_credits"]),
                    missing_reason=MissingReason.OBSERVED,
                    source_ids=enrolment_source,
                )
            )

            completeness = sum(feature.value is not None for feature in feature_rows) / len(
                feature_rows
            )
            deterministic_payload = {
                "learner_id": learner_id,
                "presentation_id": presentation_id,
                "checkpoint_week": checkpoint_week,
                "cutoff_course_day": cutoff,
                "feature_set_version": feature_set_version,
                "features": [
                    {
                        "name": feature.name,
                        "value": feature.value,
                        "missing_reason": feature.missing_reason.value,
                        "provenance_hash": feature.source_observation_hash,
                    }
                    for feature in feature_rows
                ],
            }
            states.append(
                WeeklyState(
                    state_id=state_id,
                    learner_id=learner_id,
                    presentation_id=presentation_id,
                    checkpoint_week=checkpoint_week,
                    cutoff_course_day=cutoff,
                    feature_set_version=feature_set_version,
                    data_origin=data_origin,
                    built_at=built_at,
                    is_fresh=is_fresh,
                    completeness=completeness,
                    input_hash=calculate_input_hash(deterministic_payload),
                    features=feature_rows,
                )
            )

    return states
