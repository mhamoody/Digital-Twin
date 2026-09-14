-- statement
CREATE TABLE analytics.workspace_snapshot_head (
    course_id VARCHAR(128) NOT NULL REFERENCES core.workspace_course(id),
    learner_id VARCHAR(128) NOT NULL,
    week INTEGER NOT NULL,
    state_id VARCHAR(160) NOT NULL REFERENCES analytics.workspace_snapshot(id),
    PRIMARY KEY (course_id, learner_id, week)
);
-- statement
CREATE INDEX ix_analytics_workspace_snapshot_head_state_id
    ON analytics.workspace_snapshot_head(state_id);
-- statement
CREATE TABLE analytics.workspace_automation (
    course_id VARCHAR(128) NOT NULL REFERENCES core.workspace_course(id),
    enabled BOOLEAN NOT NULL,
    version INTEGER NOT NULL,
    actor VARCHAR(128) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (course_id)
);
-- statement
CREATE TABLE analytics.workspace_runtime (
    id VARCHAR(32) NOT NULL,
    payload JSON NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);
-- statement
CREATE TABLE audit.workspace_analysis_attempt (
    id VARCHAR(64) NOT NULL,
    job_id VARCHAR(64) NOT NULL REFERENCES analytics.workspace_analysis_job(id),
    attempt INTEGER NOT NULL,
    error_code VARCHAR(128),
    outcome VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);
-- statement
CREATE INDEX ix_audit_workspace_analysis_attempt_job_id ON audit.workspace_analysis_attempt(job_id);
-- statement
CREATE TABLE analytics.workspace_analysis_plan (
    job_id VARCHAR(64) NOT NULL REFERENCES analytics.workspace_analysis_job(id),
    fingerprint VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (job_id)
);
