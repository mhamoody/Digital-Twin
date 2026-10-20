"""Read-only mapping of existing prepared OULAD states into the v2 workspace."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from digital_twin.persistence import models as old

from .contracts import CoursePolicy, EvidenceFact, LearnerSnapshot, digest
from .store import Store


def import_legacy(engine):
    dataset = {"courses": [], "enrolments": [], "events": [], "snapshots": []}
    with Session(engine) as session:
        features = defaultdict(list)
        for f in session.scalars(select(old.WeeklyFeatureRecord)):
            features[f.state_id].append(f)
        for course in session.scalars(select(old.CoursePresentation)):
            dataset["courses"].append(
                {
                    "presentation_id": course.presentation_id,
                    "title": (
                        f"{course.module_code} / {course.presentation_code} · historical course"
                    ),
                    "data_origin": course.data_origin,
                    "weeks": (course.length_days + 6) // 7,
                    "policy": CoursePolicy().model_dump(mode="json"),
                    "resources": [],
                    "assessments": [],
                    "interpretation": (
                        "Archived prepared states. Unobserved grades and course calendar "
                        "remain unavailable."
                    ),
                }
            )
        for enrol in session.scalars(select(old.Enrolment)):
            dataset["enrolments"].append(
                {
                    "presentation_id": enrol.presentation_id,
                    "learner_id": enrol.learner_id,
                    "display_name": enrol.learner_id,
                    "registration_day": enrol.registration_day,
                    "unregistration_day": enrol.unregistration_day,
                    "data_origin": enrol.data_origin,
                }
            )
        for state in session.scalars(select(old.WeeklyStateRecord)):
            facts = {
                f.feature_name: EvidenceFact(
                    evidence_id=f.evidence_id,
                    value=f.value_json,
                    status=f.missing_reason,
                    source_ids=[f.provenance_reference],
                    available_day=state.cutoff_course_day,
                )
                for f in features[state.state_id]
            }
            for name in (
                "weighted_grade_percent",
                "latest_grade_percent",
                "grade_change_points",
                "quiz_average_percent",
            ):
                facts[name] = EvidenceFact(
                    evidence_id="legacy:missing:" + digest([state.state_id, name]),
                    value=None,
                    status="not_supported",
                    unit="percent",
                )
            dataset["snapshots"].append(
                LearnerSnapshot(
                    state_id="legacy:" + digest(state.state_id),
                    presentation_id=state.presentation_id,
                    learner_id=state.learner_id,
                    checkpoint_week=state.checkpoint_week,
                    cutoff_day=state.cutoff_course_day,
                    data_origin=state.data_origin,
                    feature_version=state.feature_set_version,
                    built_at=state.built_at.isoformat(),
                    is_fresh=state.is_fresh,
                    coverage={
                        "activity": "complete",
                        "assessments": "complete",
                        "grades": "not_supported",
                        "forum": "not_supported",
                        "attendance": "not_supported",
                    },
                    course_context={
                        "interpretation": (
                            "Historical prepared evidence. No course-calendar or grade "
                            "values have been invented."
                        )
                    },
                    features=facts,
                )
            )
    if not dataset["courses"]:
        return {}
    return Store(engine).ingest_dataset(dataset)
