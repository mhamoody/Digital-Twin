-- statement
CREATE TABLE core.workspace_course (
	id VARCHAR(128) NOT NULL,
	payload JSON NOT NULL,
	PRIMARY KEY (id)
);
-- statement
CREATE TABLE analytics.workspace_policy (
	course_id VARCHAR(128) NOT NULL,
	version INTEGER NOT NULL,
	payload JSON NOT NULL,
	actor VARCHAR(128) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (course_id, version),
	FOREIGN KEY(course_id) REFERENCES core.workspace_course (id)
);
-- statement
CREATE TABLE core.workspace_enrolment (
	course_id VARCHAR(128) NOT NULL,
	learner_id VARCHAR(128) NOT NULL,
	payload JSON NOT NULL,
	PRIMARY KEY (course_id, learner_id),
	FOREIGN KEY(course_id) REFERENCES core.workspace_course (id)
);
-- statement
CREATE TABLE analytics.workspace_snapshot (
	id VARCHAR(160) NOT NULL,
	course_id VARCHAR(128) NOT NULL,
	learner_id VARCHAR(128) NOT NULL,
	week INTEGER NOT NULL,
	input_hash VARCHAR(64) NOT NULL,
	payload JSON NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(course_id, learner_id) REFERENCES core.workspace_enrolment (course_id, learner_id),
	CONSTRAINT uq_workspace_snapshot UNIQUE (course_id, learner_id, week, input_hash)
);
-- statement
CREATE INDEX ix_analytics_workspace_snapshot_course_id ON analytics.workspace_snapshot (course_id);
-- statement
CREATE INDEX ix_analytics_workspace_snapshot_learner_id ON analytics.workspace_snapshot (learner_id);
-- statement
CREATE TABLE audit.workspace_support_case (
	id VARCHAR(64) NOT NULL,
	course_id VARCHAR(128) NOT NULL,
	learner_id VARCHAR(128) NOT NULL,
	status VARCHAR(16) NOT NULL,
	version INTEGER NOT NULL,
	follow_up_day INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY(course_id, learner_id) REFERENCES core.workspace_enrolment (course_id, learner_id),
	CONSTRAINT uq_workspace_case_learner UNIQUE (course_id, learner_id),
	CONSTRAINT ck_workspace_case_status CHECK (status IN ('new','reviewed','ongoing','resolved','dismissed'))
);
-- statement
CREATE TABLE core.workspace_event (
	id VARCHAR(160) NOT NULL,
	course_id VARCHAR(128) NOT NULL,
	learner_id VARCHAR(128) NOT NULL,
	course_day INTEGER NOT NULL,
	available_day INTEGER NOT NULL,
	payload JSON NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(course_id, learner_id) REFERENCES core.workspace_enrolment (course_id, learner_id)
);
-- statement
CREATE INDEX ix_core_workspace_event_course_id ON core.workspace_event (course_id);
-- statement
CREATE INDEX ix_core_workspace_event_learner_id ON core.workspace_event (learner_id);
-- statement
CREATE TABLE analytics.workspace_analysis_job (
	id VARCHAR(64) NOT NULL,
	state_id VARCHAR(160) NOT NULL,
	policy_version INTEGER NOT NULL,
	model_kind VARCHAR(16) NOT NULL,
	expected_model_digest VARCHAR(160),
	status VARCHAR(16) NOT NULL,
	worker_id VARCHAR(128),
	lease_until TIMESTAMP WITH TIME ZONE,
	error_code VARCHAR(128),
	attempts INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_workspace_job_status CHECK (status IN ('queued','running','validated','abstained','failed')),
	FOREIGN KEY(state_id) REFERENCES analytics.workspace_snapshot (id)
);
-- statement
CREATE INDEX ix_analytics_workspace_analysis_job_state_id ON analytics.workspace_analysis_job (state_id);
-- statement
CREATE INDEX ix_analytics_workspace_analysis_job_status ON analytics.workspace_analysis_job (status);
-- statement
CREATE TABLE audit.workspace_case_event (
	id VARCHAR(64) NOT NULL,
	case_id VARCHAR(64) NOT NULL,
	actor VARCHAR(128) NOT NULL,
	request_key VARCHAR(128) NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	occurred_day INTEGER NOT NULL,
	payload JSON NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_workspace_case_request UNIQUE (actor, request_key),
	FOREIGN KEY(case_id) REFERENCES audit.workspace_support_case (id)
);
-- statement
CREATE INDEX ix_audit_workspace_case_event_case_id ON audit.workspace_case_event (case_id);
-- statement
CREATE TABLE analytics.workspace_analysis (
	id VARCHAR(64) NOT NULL,
	state_id VARCHAR(160) NOT NULL,
	policy_version INTEGER NOT NULL,
	model_kind VARCHAR(16) NOT NULL,
	payload JSON NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(id) REFERENCES analytics.workspace_analysis_job (id),
	FOREIGN KEY(state_id) REFERENCES analytics.workspace_snapshot (id)
);
-- statement
CREATE INDEX ix_analytics_workspace_analysis_state_id ON analytics.workspace_analysis (state_id);
