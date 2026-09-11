-- statement
CREATE SCHEMA IF NOT EXISTS registry;
-- statement
CREATE SCHEMA IF NOT EXISTS core;
-- statement
CREATE SCHEMA IF NOT EXISTS analytics;
-- statement
CREATE SCHEMA IF NOT EXISTS audit;

-- statement
CREATE TABLE analytics.feature_set (
    feature_set_version VARCHAR(64) NOT NULL PRIMARY KEY,
    definition_json JSONB NOT NULL,
    definition_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL
);

-- statement
CREATE TABLE analytics.model_version (
    model_ref VARCHAR(128) NOT NULL PRIMARY KEY,
    model_kind VARCHAR(32) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    config_json JSONB NOT NULL,
    config_hash VARCHAR(64) NOT NULL,
    approved_scope VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_model_kind_version UNIQUE (model_kind, model_version)
);

-- statement
CREATE TABLE registry.source_dataset (
    source_id VARCHAR(128) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    version VARCHAR(64) NOT NULL,
    licence_note TEXT NOT NULL,
    manifest_hash VARCHAR(64) NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL
);

-- statement
CREATE TABLE core.course_presentation (
    presentation_id VARCHAR(128) NOT NULL PRIMARY KEY,
    source_id VARCHAR(128) NOT NULL
        REFERENCES registry.source_dataset(source_id) ON DELETE RESTRICT,
    module_code VARCHAR(64) NOT NULL,
    presentation_code VARCHAR(64) NOT NULL,
    length_days INTEGER NOT NULL,
    data_origin VARCHAR(32) NOT NULL,
    record_hash VARCHAR(64) NOT NULL
);

-- statement
CREATE TABLE core.learner (
    learner_id VARCHAR(128) NOT NULL PRIMARY KEY,
    source_id VARCHAR(128) NOT NULL
        REFERENCES registry.source_dataset(source_id) ON DELETE RESTRICT,
    record_hash VARCHAR(64) NOT NULL
);

-- statement
CREATE TABLE registry.ingestion_run (
    run_id VARCHAR(128) NOT NULL PRIMARY KEY,
    source_id VARCHAR(128) NOT NULL
        REFERENCES registry.source_dataset(source_id) ON DELETE RESTRICT,
    adapter_version VARCHAR(64) NOT NULL,
    schema_version VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    counts_json JSONB NOT NULL,
    CONSTRAINT uq_ingestion_run_idempotency UNIQUE (idempotency_key),
    CONSTRAINT ck_ingestion_run_status
        CHECK (status IN ('started','accepted','failed'))
);

-- statement
CREATE TABLE audit.persistence_event (
    event_id VARCHAR(128) NOT NULL PRIMARY KEY,
    run_id VARCHAR(128)
        REFERENCES registry.ingestion_run(run_id) ON DELETE RESTRICT,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    action VARCHAR(32) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL
);

-- statement
CREATE TABLE core.enrolment (
    presentation_id VARCHAR(128) NOT NULL
        REFERENCES core.course_presentation(presentation_id) ON DELETE RESTRICT,
    learner_id VARCHAR(128) NOT NULL
        REFERENCES core.learner(learner_id) ON DELETE RESTRICT,
    registration_day INTEGER,
    registration_missing_reason VARCHAR(32) NOT NULL,
    unregistration_day INTEGER,
    unregistration_missing_reason VARCHAR(32) NOT NULL,
    previous_attempts INTEGER NOT NULL,
    studied_credits INTEGER NOT NULL,
    data_origin VARCHAR(32) NOT NULL,
    source_record_id VARCHAR(128) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    PRIMARY KEY (presentation_id, learner_id),
    CONSTRAINT uq_enrolment_source_record UNIQUE (source_record_id)
);

-- statement
CREATE TABLE core.source_observation (
    observation_id VARCHAR(128) NOT NULL PRIMARY KEY,
    run_id VARCHAR(128) NOT NULL
        REFERENCES registry.ingestion_run(run_id) ON DELETE RESTRICT,
    presentation_id VARCHAR(128) NOT NULL
        REFERENCES core.course_presentation(presentation_id) ON DELETE RESTRICT,
    learner_id VARCHAR(128)
        REFERENCES core.learner(learner_id) ON DELETE RESTRICT,
    observation_kind VARCHAR(32) NOT NULL,
    source_record_id VARCHAR(128) NOT NULL,
    course_day INTEGER,
    data_origin VARCHAR(32) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    CONSTRAINT ck_source_observation_origin
        CHECK (data_origin IN ('empirical','replayed','synthetic','manual_test'))
);

-- statement
CREATE TABLE analytics.weekly_state (
    state_id VARCHAR(128) NOT NULL PRIMARY KEY,
    presentation_id VARCHAR(128) NOT NULL,
    learner_id VARCHAR(128) NOT NULL,
    checkpoint_week INTEGER NOT NULL,
    cutoff_course_day INTEGER NOT NULL,
    feature_set_version VARCHAR(64) NOT NULL
        REFERENCES analytics.feature_set(feature_set_version) ON DELETE RESTRICT,
    built_at TIMESTAMPTZ NOT NULL,
    is_fresh BOOLEAN NOT NULL,
    completeness DOUBLE PRECISION NOT NULL,
    input_hash VARCHAR(64) NOT NULL,
    data_origin VARCHAR(32) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    CONSTRAINT fk_weekly_state_enrolment
        FOREIGN KEY (presentation_id, learner_id)
        REFERENCES core.enrolment(presentation_id, learner_id) ON DELETE RESTRICT,
    CONSTRAINT uq_weekly_state_grain UNIQUE
        (presentation_id, learner_id, checkpoint_week, feature_set_version),
    CONSTRAINT ck_weekly_state_week CHECK (checkpoint_week >= 1),
    CONSTRAINT ck_state_complete CHECK (completeness >= 0 AND completeness <= 1),
    CONSTRAINT ck_weekly_state_origin
        CHECK (data_origin IN ('empirical','replayed','synthetic','manual_test'))
);

-- statement
CREATE TABLE analytics.prediction (
    prediction_id VARCHAR(128) NOT NULL PRIMARY KEY,
    state_id VARCHAR(128) NOT NULL
        REFERENCES analytics.weekly_state(state_id) ON DELETE RESTRICT,
    model_ref VARCHAR(128) NOT NULL
        REFERENCES analytics.model_version(model_ref) ON DELETE RESTRICT,
    raw_risk_score DOUBLE PRECISION,
    display_probability DOUBLE PRECISION,
    calibration_version VARCHAR(64),
    risk_band VARCHAR(16),
    uncertainty_note VARCHAR(300) NOT NULL,
    abstain BOOLEAN NOT NULL,
    abstention_reason VARCHAR(200),
    quality_gate_passed BOOLEAN NOT NULL,
    fallback_used BOOLEAN NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    data_origin VARCHAR(32) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    CONSTRAINT ck_prediction_raw_score CHECK
        (raw_risk_score IS NULL OR raw_risk_score BETWEEN 0 AND 1),
    CONSTRAINT ck_prediction_display_score CHECK
        (display_probability IS NULL OR display_probability BETWEEN 0 AND 1),
    CONSTRAINT ck_prediction_origin
        CHECK (data_origin IN ('empirical','replayed','synthetic','manual_test'))
);

-- statement
CREATE TABLE analytics.weekly_feature (
    state_id VARCHAR(128) NOT NULL
        REFERENCES analytics.weekly_state(state_id) ON DELETE RESTRICT,
    feature_name VARCHAR(128) NOT NULL,
    value_json JSONB,
    missing_reason VARCHAR(32) NOT NULL,
    evidence_id VARCHAR(128) NOT NULL,
    provenance_reference VARCHAR(128) NOT NULL,
    source_observation_count INTEGER NOT NULL,
    source_observation_hash VARCHAR(64) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    PRIMARY KEY (state_id, feature_name),
    CONSTRAINT uq_weekly_feature_evidence UNIQUE (evidence_id),
    CONSTRAINT ck_feature_source_count CHECK (source_observation_count >= 0)
);

-- statement
CREATE TABLE analytics.alert (
    alert_id VARCHAR(128) NOT NULL PRIMARY KEY,
    prediction_id VARCHAR(128) NOT NULL
        REFERENCES analytics.prediction(prediction_id) ON DELETE RESTRICT,
    state_id VARCHAR(128) NOT NULL
        REFERENCES analytics.weekly_state(state_id) ON DELETE RESTRICT,
    policy_version VARCHAR(64) NOT NULL,
    priority VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    is_fresh BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    data_origin VARCHAR(32) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    CONSTRAINT ck_alert_status
        CHECK (status IN ('new','reviewed','resolved','dismissed')),
    CONSTRAINT ck_alert_origin
        CHECK (data_origin IN ('empirical','replayed','synthetic','manual_test'))
);

-- statement
CREATE TABLE analytics.feature_source_sample (
    state_id VARCHAR(128) NOT NULL,
    feature_name VARCHAR(128) NOT NULL,
    observation_id VARCHAR(128) NOT NULL
        REFERENCES core.source_observation(observation_id) ON DELETE RESTRICT,
    PRIMARY KEY (state_id, feature_name, observation_id),
    CONSTRAINT fk_feature_source_sample_feature
        FOREIGN KEY (state_id, feature_name)
        REFERENCES analytics.weekly_feature(state_id, feature_name) ON DELETE RESTRICT
);

-- statement
CREATE TABLE analytics.prediction_action (
    prediction_id VARCHAR(128) NOT NULL
        REFERENCES analytics.prediction(prediction_id) ON DELETE RESTRICT,
    action_index INTEGER NOT NULL,
    action_code VARCHAR(64) NOT NULL,
    PRIMARY KEY (prediction_id, action_index)
);

-- statement
CREATE TABLE analytics.prediction_claim (
    prediction_id VARCHAR(128) NOT NULL
        REFERENCES analytics.prediction(prediction_id) ON DELETE RESTRICT,
    claim_index INTEGER NOT NULL,
    evidence_id VARCHAR(128) NOT NULL
        REFERENCES analytics.weekly_feature(evidence_id) ON DELETE RESTRICT,
    claim_code VARCHAR(64) NOT NULL,
    PRIMARY KEY (prediction_id, claim_index, evidence_id)
);

-- statement
CREATE TABLE analytics.alert_evidence (
    alert_id VARCHAR(128) NOT NULL
        REFERENCES analytics.alert(alert_id) ON DELETE RESTRICT,
    evidence_id VARCHAR(128) NOT NULL
        REFERENCES analytics.weekly_feature(evidence_id) ON DELETE RESTRICT,
    PRIMARY KEY (alert_id, evidence_id)
);

-- statement
CREATE TABLE analytics.alert_review (
    review_id VARCHAR(128) NOT NULL PRIMARY KEY,
    alert_id VARCHAR(128) NOT NULL
        REFERENCES analytics.alert(alert_id) ON DELETE RESTRICT,
    reviewer_id VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(64) NOT NULL,
    previous_status VARCHAR(16) NOT NULL,
    new_status VARCHAR(16) NOT NULL,
    note TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    CONSTRAINT ck_review_new_status
        CHECK (new_status IN ('reviewed','resolved','dismissed'))
);
