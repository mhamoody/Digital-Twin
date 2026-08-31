"""Read models and audited review operations for the HTTP boundary."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, case, func, inspect, select, text
from sqlalchemy.orm import Session

from digital_twin.persistence import PersistenceConflict, TwinStore
from digital_twin.persistence.models import (
    AlertEvidence,
    AlertRecord,
    AlertReview,
    CoursePresentation,
    Enrolment,
    FeatureSourceSample,
    ModelVersion,
    PredictionAction,
    PredictionClaim,
    PredictionRecord,
    SourceObservation,
    WeeklyFeatureRecord,
    WeeklyStateRecord,
)

from .schemas import (
    AlertDetail,
    AlertListItem,
    AlertListResponse,
    AlertReviewRequest,
    AlertReviewResponse,
    ClaimResponse,
    EvidenceResponse,
    LearnerActivityWeek,
    LearnerDetailResponse,
    LearnerFeatureResponse,
    LearnerListItem,
    LearnerListResponse,
    PredictionTimelinePoint,
    PresentationOverview,
    ReviewHistoryItem,
)


class ResourceNotFound(LookupError):
    pass


class ReviewConflict(RuntimeError):
    pass


class ApiService:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.store = TwinStore(engine)

    def readiness(self) -> tuple[str, str]:
        table_names = set(inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if "alembic_version" in table_names:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
            elif self.engine.dialect.name == "sqlite" and {
                "course_presentation",
                "weekly_state",
                "prediction",
                "alert",
                "sync_cursor",
            }.issubset(table_names):
                revision = "sqlite-pilot-schema"
            else:
                raise LookupError("The database schema is not initialized.")
        return self.engine.dialect.name, revision

    def presentation_overview(self, presentation_id: str) -> PresentationOverview:
        with Session(self.engine) as session:
            presentation = session.get(CoursePresentation, presentation_id)
            if presentation is None:
                raise ResourceNotFound(presentation_id)
            learner_count = (
                session.scalar(
                    select(func.count())
                    .select_from(Enrolment)
                    .where(Enrolment.presentation_id == presentation_id)
                )
                or 0
            )
            state_count = (
                session.scalar(
                    select(func.count())
                    .select_from(WeeklyStateRecord)
                    .where(WeeklyStateRecord.presentation_id == presentation_id)
                )
                or 0
            )
            prediction_count = (
                session.scalar(
                    select(func.count())
                    .select_from(PredictionRecord)
                    .join(WeeklyStateRecord)
                    .where(WeeklyStateRecord.presentation_id == presentation_id)
                )
                or 0
            )
            alert_rows = session.execute(
                select(AlertRecord.status, func.count())
                .join(WeeklyStateRecord, AlertRecord.state_id == WeeklyStateRecord.state_id)
                .where(WeeklyStateRecord.presentation_id == presentation_id)
                .group_by(AlertRecord.status)
            ).all()
            checkpoint_rows = session.execute(
                select(WeeklyStateRecord.checkpoint_week, func.count())
                .where(WeeklyStateRecord.presentation_id == presentation_id)
                .group_by(WeeklyStateRecord.checkpoint_week)
            ).all()
            latest_built = session.scalar(
                select(func.max(WeeklyStateRecord.built_at)).where(
                    WeeklyStateRecord.presentation_id == presentation_id
                )
            )
            stale_alerts = (
                session.scalar(
                    select(func.count())
                    .select_from(AlertRecord)
                    .join(WeeklyStateRecord, AlertRecord.state_id == WeeklyStateRecord.state_id)
                    .where(
                        WeeklyStateRecord.presentation_id == presentation_id,
                        AlertRecord.is_fresh.is_(False),
                    )
                )
                or 0
            )
        sync = self.store.sync_snapshot(presentation_id=presentation_id, now=datetime.now(UTC))
        alerts_by_status = {status: count for status, count in alert_rows}
        ingestion_status = sync["status"]
        alerts_fresh = stale_alerts == 0 and ingestion_status not in {"stale", "failed"}
        return PresentationOverview(
            presentation_id=presentation.presentation_id,
            module_code=presentation.module_code,
            presentation_code=presentation.presentation_code,
            data_origin=presentation.data_origin,
            learner_count=learner_count,
            state_count=state_count,
            prediction_count=prediction_count,
            alert_count=sum(alerts_by_status.values()),
            alerts_by_status=alerts_by_status,
            states_by_checkpoint={week: count for week, count in checkpoint_rows},
            latest_state_built_at=latest_built,
            all_current_alerts_fresh=alerts_fresh,
            ingestion_status=ingestion_status,
            last_ingestion_success_at=sync.get("last_success_at"),
            ingestion_age_minutes=sync.get("age_minutes"),
            active_quarantine_count=sync.get("active_quarantine_count", 0),
        )

    def list_alerts(
        self,
        *,
        presentation_id: str | None,
        alert_status: str | None,
        limit: int,
        offset: int,
    ) -> AlertListResponse:
        conditions = []
        if presentation_id:
            conditions.append(WeeklyStateRecord.presentation_id == presentation_id)
        if alert_status:
            conditions.append(AlertRecord.status == alert_status)
        base = (
            select(
                AlertRecord,
                PredictionRecord,
                WeeklyStateRecord,
                ModelVersion,
                func.count(AlertEvidence.evidence_id).label("evidence_count"),
            )
            .join(PredictionRecord, AlertRecord.prediction_id == PredictionRecord.prediction_id)
            .join(WeeklyStateRecord, AlertRecord.state_id == WeeklyStateRecord.state_id)
            .join(ModelVersion, PredictionRecord.model_ref == ModelVersion.model_ref)
            .outerjoin(AlertEvidence, AlertRecord.alert_id == AlertEvidence.alert_id)
            .where(*conditions)
            .group_by(
                AlertRecord.alert_id,
                PredictionRecord.prediction_id,
                WeeklyStateRecord.state_id,
                ModelVersion.model_ref,
            )
        )
        priority_order = case(
            (AlertRecord.priority == "high", 0),
            (AlertRecord.priority == "medium", 1),
            else_=2,
        )
        count_statement = (
            select(func.count())
            .select_from(AlertRecord)
            .join(WeeklyStateRecord, AlertRecord.state_id == WeeklyStateRecord.state_id)
            .where(*conditions)
        )
        with Session(self.engine) as session:
            total = session.scalar(count_statement) or 0
            rows = session.execute(
                base.order_by(
                    priority_order,
                    PredictionRecord.display_probability.desc(),
                    AlertRecord.alert_id,
                )
                .limit(limit)
                .offset(offset)
            ).all()
        return AlertListResponse(
            items=[self._alert_item(*row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def list_learners(
        self,
        *,
        presentation_id: str,
        query: str | None,
        limit: int,
        offset: int,
    ) -> LearnerListResponse:
        """Return the course roster, including learners who have no alert."""

        conditions = [Enrolment.presentation_id == presentation_id]
        if query:
            conditions.append(Enrolment.learner_id.ilike(f"%{query}%"))
        with Session(self.engine) as session:
            if session.get(CoursePresentation, presentation_id) is None:
                raise ResourceNotFound(presentation_id)
            total = (
                session.scalar(select(func.count()).select_from(Enrolment).where(*conditions)) or 0
            )
            enrolments = session.scalars(
                select(Enrolment)
                .where(*conditions)
                .order_by(Enrolment.learner_id)
                .limit(limit)
                .offset(offset)
            ).all()
            items = self._learner_items(session, enrolments)
        return LearnerListResponse(items=items, total=total, limit=limit, offset=offset)

    def learner_detail(self, *, presentation_id: str, learner_id: str) -> LearnerDetailResponse:
        """Return one instructor-safe learner view at the requested course context."""

        with Session(self.engine) as session:
            enrolment = session.get(Enrolment, (presentation_id, learner_id))
            if enrolment is None:
                raise ResourceNotFound(f"{presentation_id}/{learner_id}")
            learner_item = self._learner_items(session, [enrolment])[0]
            latest_state = session.scalar(
                select(WeeklyStateRecord)
                .where(
                    WeeklyStateRecord.presentation_id == presentation_id,
                    WeeklyStateRecord.learner_id == learner_id,
                )
                .order_by(
                    WeeklyStateRecord.checkpoint_week.desc(),
                    WeeklyStateRecord.built_at.desc(),
                    WeeklyStateRecord.state_id.desc(),
                )
                .limit(1)
            )
            features = []
            if latest_state is not None:
                feature_rows = session.scalars(
                    select(WeeklyFeatureRecord)
                    .where(WeeklyFeatureRecord.state_id == latest_state.state_id)
                    .order_by(WeeklyFeatureRecord.feature_name)
                ).all()
                features = [
                    LearnerFeatureResponse(
                        evidence_id=feature.evidence_id,
                        feature_name=feature.feature_name,
                        value=feature.value_json,
                        missing_reason=feature.missing_reason,
                        source_observation_count=feature.source_observation_count,
                    )
                    for feature in feature_rows
                ]

            observation_rows = session.scalars(
                select(SourceObservation)
                .where(
                    SourceObservation.presentation_id == presentation_id,
                    SourceObservation.learner_id == learner_id,
                    SourceObservation.course_day.is_not(None),
                    SourceObservation.course_day >= 0,
                )
                .order_by(SourceObservation.course_day, SourceObservation.observation_id)
            ).all()
            weekly_activity: dict[int, dict[str, int]] = defaultdict(
                lambda: {"activity_count": 0, "assessment_event_count": 0}
            )
            for observation in observation_rows:
                course_week = observation.course_day // 7 + 1
                amount = observation.event_count if observation.event_count is not None else 1
                if observation.observation_kind == "activity":
                    weekly_activity[course_week]["activity_count"] += amount
                elif observation.observation_kind == "assessment":
                    weekly_activity[course_week]["assessment_event_count"] += 1

            timeline_rows = session.execute(
                select(PredictionRecord, WeeklyStateRecord, ModelVersion)
                .join(WeeklyStateRecord, PredictionRecord.state_id == WeeklyStateRecord.state_id)
                .join(ModelVersion, PredictionRecord.model_ref == ModelVersion.model_ref)
                .where(
                    WeeklyStateRecord.presentation_id == presentation_id,
                    WeeklyStateRecord.learner_id == learner_id,
                )
                .order_by(
                    WeeklyStateRecord.checkpoint_week,
                    PredictionRecord.generated_at,
                    PredictionRecord.prediction_id,
                )
            ).all()
            selected_alert_id = learner_item.alert_id
            selected_prediction_id = None
            if selected_alert_id:
                selected_prediction_id = session.scalar(
                    select(AlertRecord.prediction_id).where(
                        AlertRecord.alert_id == selected_alert_id
                    )
                )

        return LearnerDetailResponse(
            learner=learner_item,
            registration_day=enrolment.registration_day,
            registration_missing_reason=enrolment.registration_missing_reason,
            unregistration_day=enrolment.unregistration_day,
            unregistration_missing_reason=enrolment.unregistration_missing_reason,
            features=features,
            activity_timeline=[
                LearnerActivityWeek(course_week=week, **counts)
                for week, counts in sorted(weekly_activity.items())
            ],
            prediction_timeline=[
                PredictionTimelinePoint(
                    checkpoint_week=state.checkpoint_week,
                    cutoff_course_day=state.cutoff_course_day,
                    display_probability=prediction.display_probability,
                    risk_band=prediction.risk_band,
                    model_version=model.model_version,
                    generated_at=prediction.generated_at,
                    is_selected_alert=prediction.prediction_id == selected_prediction_id,
                )
                for prediction, state, model in timeline_rows
            ],
        )

    def alert_detail(self, alert_id: str) -> AlertDetail:
        with Session(self.engine) as session:
            row = session.execute(
                select(AlertRecord, PredictionRecord, WeeklyStateRecord, ModelVersion)
                .join(PredictionRecord, AlertRecord.prediction_id == PredictionRecord.prediction_id)
                .join(WeeklyStateRecord, AlertRecord.state_id == WeeklyStateRecord.state_id)
                .join(ModelVersion, PredictionRecord.model_ref == ModelVersion.model_ref)
                .where(AlertRecord.alert_id == alert_id)
            ).one_or_none()
            if row is None:
                raise ResourceNotFound(alert_id)
            alert, prediction, state, model = row
            evidence_ids = session.scalars(
                select(AlertEvidence.evidence_id)
                .where(AlertEvidence.alert_id == alert_id)
                .order_by(AlertEvidence.evidence_id)
            ).all()
            evidence_count = len(evidence_ids)
            claim_rows = session.execute(
                select(
                    PredictionClaim.claim_index,
                    PredictionClaim.claim_code,
                    PredictionClaim.evidence_id,
                )
                .where(PredictionClaim.prediction_id == prediction.prediction_id)
                .order_by(PredictionClaim.claim_index, PredictionClaim.evidence_id)
            ).all()
            actions = session.scalars(
                select(PredictionAction.action_code)
                .where(PredictionAction.prediction_id == prediction.prediction_id)
                .order_by(PredictionAction.action_index)
            ).all()
            features = session.scalars(
                select(WeeklyFeatureRecord)
                .where(WeeklyFeatureRecord.evidence_id.in_(evidence_ids))
                .order_by(WeeklyFeatureRecord.feature_name)
            ).all()
            sample_rows = session.execute(
                select(
                    WeeklyFeatureRecord.evidence_id,
                    SourceObservation.source_record_id,
                )
                .join(
                    FeatureSourceSample,
                    (WeeklyFeatureRecord.state_id == FeatureSourceSample.state_id)
                    & (WeeklyFeatureRecord.feature_name == FeatureSourceSample.feature_name),
                )
                .join(
                    SourceObservation,
                    FeatureSourceSample.observation_id == SourceObservation.observation_id,
                )
                .where(WeeklyFeatureRecord.evidence_id.in_(evidence_ids))
                .order_by(WeeklyFeatureRecord.evidence_id, SourceObservation.source_record_id)
            ).all()
            reviews = session.scalars(
                select(AlertReview)
                .where(AlertReview.alert_id == alert_id)
                .order_by(AlertReview.reviewed_at, AlertReview.review_id)
            ).all()
            timeline_rows = session.execute(
                select(PredictionRecord, WeeklyStateRecord, ModelVersion)
                .join(
                    WeeklyStateRecord,
                    PredictionRecord.state_id == WeeklyStateRecord.state_id,
                )
                .join(ModelVersion, PredictionRecord.model_ref == ModelVersion.model_ref)
                .where(
                    WeeklyStateRecord.learner_id == state.learner_id,
                    WeeklyStateRecord.presentation_id == state.presentation_id,
                )
                .order_by(
                    WeeklyStateRecord.checkpoint_week,
                    PredictionRecord.generated_at,
                    PredictionRecord.prediction_id,
                )
            ).all()

        grouped_claims: dict[int, dict[str, Any]] = {}
        for index, code, evidence_id in claim_rows:
            grouped_claims.setdefault(index, {"claim_code": code, "evidence_ids": []})[
                "evidence_ids"
            ].append(evidence_id)
        samples: dict[str, list[str]] = defaultdict(list)
        for evidence_id, source_record_id in sample_rows:
            samples[evidence_id].append(source_record_id)
        return AlertDetail(
            alert=self._alert_item(alert, prediction, state, model, evidence_count),
            state_id=state.state_id,
            input_hash=state.input_hash,
            feature_set_version=state.feature_set_version,
            completeness=state.completeness,
            model_ref=model.model_ref,
            uncertainty_note=prediction.uncertainty_note,
            quality_gate_passed=prediction.quality_gate_passed,
            fallback_used=prediction.fallback_used,
            claims=[ClaimResponse(**value) for _, value in sorted(grouped_claims.items())],
            suggested_actions=list(actions),
            evidence=[
                EvidenceResponse(
                    evidence_id=feature.evidence_id,
                    feature_name=feature.feature_name,
                    value=feature.value_json,
                    missing_reason=feature.missing_reason,
                    source_observation_count=feature.source_observation_count,
                    source_observation_hash=feature.source_observation_hash,
                    source_record_samples=samples[feature.evidence_id],
                )
                for feature in features
            ],
            prediction_timeline=[
                PredictionTimelinePoint(
                    checkpoint_week=timeline_state.checkpoint_week,
                    cutoff_course_day=timeline_state.cutoff_course_day,
                    display_probability=timeline_prediction.display_probability,
                    risk_band=timeline_prediction.risk_band,
                    model_version=timeline_model.model_version,
                    generated_at=timeline_prediction.generated_at,
                    is_selected_alert=timeline_prediction.prediction_id == prediction.prediction_id,
                )
                for timeline_prediction, timeline_state, timeline_model in timeline_rows
            ],
            review_history=[
                ReviewHistoryItem(
                    review_id=review.review_id,
                    reviewer_id=review.reviewer_id,
                    reviewer_role=review.reviewer_role,
                    previous_status=review.previous_status,
                    new_status=review.new_status,
                    note=review.note,
                    reviewed_at=review.reviewed_at,
                )
                for review in reviews
            ],
        )

    def review_alert(
        self,
        *,
        alert_id: str,
        identity_id: str,
        identity_role: str,
        idempotency_key: str,
        request: AlertReviewRequest,
    ) -> AlertReviewResponse:
        digest = hashlib.sha256(f"{alert_id}:{identity_id}:{idempotency_key}".encode()).hexdigest()[
            :24
        ]
        review_id = f"review:api:{digest}"
        reviewed_at = datetime.now(UTC)
        try:
            created = self.store.review_alert(
                review_id=review_id,
                alert_id=alert_id,
                reviewer_id=identity_id,
                reviewer_role=identity_role,
                new_status=request.new_status.value,
                note=request.note,
                reviewed_at=reviewed_at,
            )
        except KeyError as error:
            raise ResourceNotFound(alert_id) from error
        except (ValueError, PersistenceConflict) as error:
            raise ReviewConflict(str(error)) from error
        if not created:
            with Session(self.engine) as session:
                existing = session.get(AlertReview, review_id)
                assert existing is not None
                reviewed_at = existing.reviewed_at
        return AlertReviewResponse(
            review_id=review_id,
            alert_id=alert_id,
            status=request.new_status,
            created=created,
            reviewed_at=reviewed_at,
        )

    @staticmethod
    def _alert_item(
        alert: AlertRecord,
        prediction: PredictionRecord,
        state: WeeklyStateRecord,
        model: ModelVersion,
        evidence_count: int,
    ) -> AlertListItem:
        if prediction.display_probability is None or prediction.risk_band is None:
            raise RuntimeError("persisted alert is linked to an incomplete prediction")
        return AlertListItem(
            alert_id=alert.alert_id,
            learner_id=state.learner_id,
            presentation_id=state.presentation_id,
            checkpoint_week=state.checkpoint_week,
            cutoff_course_day=state.cutoff_course_day,
            display_probability=prediction.display_probability,
            risk_band=prediction.risk_band,
            model_kind=model.model_kind,
            model_version=model.model_version,
            priority=alert.priority,
            status=alert.status,
            is_fresh=alert.is_fresh,
            generated_at=prediction.generated_at,
            data_origin=alert.data_origin,
            evidence_count=evidence_count,
        )

    @staticmethod
    def _learner_items(session: Session, enrolments: list[Enrolment]) -> list[LearnerListItem]:
        if not enrolments:
            return []
        presentation_id = enrolments[0].presentation_id
        learner_ids = [enrolment.learner_id for enrolment in enrolments]
        state_rows = session.scalars(
            select(WeeklyStateRecord)
            .where(
                WeeklyStateRecord.presentation_id == presentation_id,
                WeeklyStateRecord.learner_id.in_(learner_ids),
            )
            .order_by(
                WeeklyStateRecord.learner_id,
                WeeklyStateRecord.checkpoint_week.desc(),
                WeeklyStateRecord.built_at.desc(),
                WeeklyStateRecord.state_id.desc(),
            )
        ).all()
        latest_states: dict[str, WeeklyStateRecord] = {}
        for state in state_rows:
            latest_states.setdefault(state.learner_id, state)

        all_state_ids = [state.state_id for state in state_rows]
        prediction_rows = []
        if all_state_ids:
            prediction_rows = session.execute(
                select(PredictionRecord, WeeklyStateRecord, ModelVersion)
                .join(WeeklyStateRecord, PredictionRecord.state_id == WeeklyStateRecord.state_id)
                .join(ModelVersion, PredictionRecord.model_ref == ModelVersion.model_ref)
                .where(PredictionRecord.state_id.in_(all_state_ids))
                .order_by(
                    WeeklyStateRecord.learner_id,
                    WeeklyStateRecord.checkpoint_week.desc(),
                    PredictionRecord.generated_at.desc(),
                    PredictionRecord.prediction_id.desc(),
                )
            ).all()
        predictions_by_learner: dict[str, list[tuple[PredictionRecord, ModelVersion]]] = (
            defaultdict(list)
        )
        seen_checkpoint: set[tuple[str, int]] = set()
        for prediction, state, model in prediction_rows:
            checkpoint_key = (state.learner_id, state.checkpoint_week)
            if checkpoint_key in seen_checkpoint:
                continue
            seen_checkpoint.add(checkpoint_key)
            predictions_by_learner[state.learner_id].append((prediction, model))

        latest_prediction_ids = [
            values[0][0].prediction_id for values in predictions_by_learner.values() if values
        ]
        latest_state_ids = [state.state_id for state in latest_states.values()]
        summary_features: dict[str, dict[str, Any]] = defaultdict(dict)
        summary_feature_names = {
            "clicks_last_14",
            "active_days_last_14",
            "days_since_last_activity",
            "assessments_due",
            "assessments_submitted",
            "assessments_missed",
            "submission_rate",
        }
        if latest_state_ids:
            feature_rows = session.scalars(
                select(WeeklyFeatureRecord).where(
                    WeeklyFeatureRecord.state_id.in_(latest_state_ids),
                    WeeklyFeatureRecord.feature_name.in_(summary_feature_names),
                )
            ).all()
            for feature in feature_rows:
                summary_features[feature.state_id][feature.feature_name] = feature.value_json
        alerts_by_prediction: dict[str, tuple[AlertRecord, int]] = {}
        if latest_prediction_ids:
            alert_rows = session.execute(
                select(
                    AlertRecord,
                    func.count(AlertEvidence.evidence_id).label("evidence_count"),
                )
                .outerjoin(AlertEvidence, AlertRecord.alert_id == AlertEvidence.alert_id)
                .where(AlertRecord.prediction_id.in_(latest_prediction_ids))
                .group_by(AlertRecord.alert_id)
                .order_by(AlertRecord.created_at.desc(), AlertRecord.alert_id.desc())
            ).all()
            for alert, evidence_count in alert_rows:
                alerts_by_prediction.setdefault(alert.prediction_id, (alert, evidence_count))

        items = []
        for enrolment in enrolments:
            state = latest_states.get(enrolment.learner_id)
            learner_predictions = predictions_by_learner.get(enrolment.learner_id, [])
            latest = learner_predictions[0] if learner_predictions else None
            previous = learner_predictions[1] if len(learner_predictions) > 1 else None
            prediction = latest[0] if latest else None
            model = latest[1] if latest else None
            previous_probability = previous[0].display_probability if previous else None
            probability_change = None
            if (
                prediction is not None
                and prediction.display_probability is not None
                and previous_probability is not None
            ):
                probability_change = prediction.display_probability - previous_probability
            alert_row = alerts_by_prediction.get(prediction.prediction_id) if prediction else None
            alert = alert_row[0] if alert_row else None
            state_features = summary_features.get(state.state_id, {}) if state else {}
            items.append(
                LearnerListItem(
                    learner_id=enrolment.learner_id,
                    presentation_id=enrolment.presentation_id,
                    data_origin=enrolment.data_origin,
                    latest_checkpoint_week=state.checkpoint_week if state else None,
                    latest_cutoff_course_day=state.cutoff_course_day if state else None,
                    completeness=state.completeness if state else None,
                    is_fresh=state.is_fresh if state else None,
                    display_probability=prediction.display_probability if prediction else None,
                    previous_probability=previous_probability,
                    probability_change=probability_change,
                    risk_band=prediction.risk_band if prediction else None,
                    model_version=model.model_version if model else None,
                    alert_id=alert.alert_id if alert else None,
                    alert_status=alert.status if alert else None,
                    evidence_count=alert_row[1] if alert_row else 0,
                    activity_count_14d=state_features.get("clicks_last_14"),
                    active_days_14d=state_features.get("active_days_last_14"),
                    days_since_last_activity=state_features.get("days_since_last_activity"),
                    assessments_due=state_features.get("assessments_due"),
                    assessments_submitted=state_features.get("assessments_submitted"),
                    assessments_missed=state_features.get("assessments_missed"),
                    submission_rate=state_features.get("submission_rate"),
                )
            )
        return items
