-- statement
ALTER TABLE core.source_observation
    ADD COLUMN event_code VARCHAR(128),
    ADD COLUMN event_at TIMESTAMPTZ,
    ADD COLUMN available_at TIMESTAMPTZ,
    ADD COLUMN time_precision VARCHAR(32),
    ADD COLUMN value_json JSONB,
    ADD COLUMN event_count INTEGER,
    ADD COLUMN adapter_version VARCHAR(64),
    ADD COLUMN metadata_json JSONB,
    ADD CONSTRAINT ck_source_observation_event_count
        CHECK (event_count IS NULL OR event_count >= 0);

-- statement
CREATE TABLE registry.sync_cursor (
    connector_id VARCHAR(128) NOT NULL PRIMARY KEY,
    source_id VARCHAR(128) NOT NULL
        REFERENCES registry.source_dataset(source_id) ON DELETE RESTRICT,
    presentation_id VARCHAR(128) NOT NULL UNIQUE
        REFERENCES core.course_presentation(presentation_id) ON DELETE RESTRICT,
    cursor_at TIMESTAMPTZ,
    cursor_key VARCHAR(128),
    last_success_at TIMESTAMPTZ,
    status VARCHAR(16) NOT NULL,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    quarantined_count INTEGER NOT NULL DEFAULT 0,
    stale_after_minutes INTEGER NOT NULL DEFAULT 60,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_sync_cursor_status CHECK (status IN ('current','failed')),
    CONSTRAINT ck_sync_cursor_failures CHECK (consecutive_failures >= 0),
    CONSTRAINT ck_sync_cursor_processed CHECK (processed_count >= 0),
    CONSTRAINT ck_sync_cursor_quarantined CHECK (quarantined_count >= 0),
    CONSTRAINT ck_sync_cursor_stale_after CHECK (stale_after_minutes > 0)
);

-- statement
CREATE TABLE registry.quarantined_record (
    quarantine_id VARCHAR(128) NOT NULL PRIMARY KEY,
    connector_id VARCHAR(128) NOT NULL
        REFERENCES registry.sync_cursor(connector_id) ON DELETE RESTRICT,
    source_record_id VARCHAR(128) NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    error_json JSONB NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    recovered_at TIMESTAMPTZ,
    recovery_run_id VARCHAR(128)
        REFERENCES registry.ingestion_run(run_id) ON DELETE RESTRICT,
    CONSTRAINT uq_quarantine_connector_record
        UNIQUE (connector_id, source_record_id)
);
