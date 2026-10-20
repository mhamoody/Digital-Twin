from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from digital_twin.api.app import create_app
from digital_twin.api.service import ApiService
from digital_twin.persistence.database import create_twin_engine, create_validation_schema
from digital_twin.persistence import models as m

NOW = datetime(2026, 1, 1, tzinfo=UTC)

@pytest.fixture
def engine():
    engine = create_twin_engine("sqlite+pysqlite:///:memory:")
    create_validation_schema(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def service(engine):
    return ApiService(engine)

@pytest.fixture
def client(engine, monkeypatch, tmp_path):
    grants = tmp_path / "course-grants.json"
    grants.write_text('{"instructor:test": ["oulad:AAA:2013J"]}', encoding="utf-8")
    monkeypatch.setenv("DIGITAL_TWIN_DEVELOPMENT_AUTH", "1")
    monkeypatch.setenv("DIGITAL_TWIN_COURSE_GRANTS_FILE", str(grants))
    with TestClient(create_app(engine=engine)) as client:
        yield client

@pytest.fixture
def seed(engine):
    def insert(model, **values):
        with Session(engine) as session, session.begin():
            session.add(model(**values))
    insert(m.SourceDataset, source_id="test", name="Test", version="v1",
           licence_note="Synthetic test fixture", manifest_hash="h", imported_at=NOW)
    insert(m.FeatureSet, feature_set_version="v1", definition_json={}, definition_hash="h", created_at=NOW)
    def populate(week, *, learner="l1", course="oulad:AAA:2013J", prediction=True,
                 model="v1", calibration="test-cal-v1", abstain=False):
        with Session(engine) as session, session.begin():
            if session.get(m.CoursePresentation, course) is None:
                session.add(m.CoursePresentation(presentation_id=course, source_id="test", module_code="AAA",
                    presentation_code="test", length_days=112, data_origin="synthetic", record_hash="h"))
                session.flush()
            if session.get(m.Learner, learner) is None:
                session.add(m.Learner(learner_id=learner, source_id="test", record_hash="h"))
                session.flush()
            if session.get(m.Enrolment, (course, learner)) is None:
                session.add(m.Enrolment(presentation_id=course, learner_id=learner,
                    registration_day=0, registration_missing_reason="observed",
                    unregistration_missing_reason="not_applicable", previous_attempts=0, studied_credits=60,
                    data_origin="synthetic", source_record_id=course+learner, record_hash="h"))
                session.flush()
            sid=f"{course}:{learner}:w{week}"
            session.add(m.WeeklyStateRecord(state_id=sid, presentation_id=course, learner_id=learner,
                checkpoint_week=week, cutoff_course_day=week*7-1, feature_set_version="v1",
                built_at=NOW, is_fresh=True, completeness=1, input_hash="h", data_origin="synthetic", record_hash="h"))
            session.flush()
            if prediction:
                if session.get(m.ModelVersion, model) is None:
                    session.add(m.ModelVersion(model_ref=model, model_kind="llm", model_version=model,
                        config_json={}, config_hash="h", approved_scope="integration_demo_only", created_at=NOW))
                    session.flush()
                session.add(m.PredictionRecord(prediction_id="p:"+sid, state_id=sid, model_ref=model,
                    raw_risk_score=None if abstain else week/10,
                    display_probability=None if abstain else week/10,
                    calibration_version=calibration, risk_band=None if abstain else "high",
                    uncertainty_note="test", abstain=abstain, abstention_reason="test" if abstain else None,
                    quality_gate_passed=True, fallback_used=False, generated_at=NOW,
                    data_origin="synthetic", record_hash="h"))
        return sid
    return populate
