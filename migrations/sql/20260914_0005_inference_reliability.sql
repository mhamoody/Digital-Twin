-- statement
CREATE TABLE analytics.workspace_course_analysis_control (
    course_id VARCHAR(128) NOT NULL REFERENCES core.workspace_course(id),
    payload JSON NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (course_id)
);
-- statement
CREATE TABLE audit.workspace_inference_trace (
    id VARCHAR(64) NOT NULL,
    job_id VARCHAR(64) NOT NULL REFERENCES analytics.workspace_analysis_job(id),
    job_attempt INTEGER NOT NULL,
    generation INTEGER NOT NULL,
    payload JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_workspace_inference_generation UNIQUE (job_id, job_attempt, generation)
);
-- statement
CREATE INDEX ix_audit_workspace_inference_trace_job_id ON audit.workspace_inference_trace(job_id);
