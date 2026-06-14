-- liquibase formatted sql
-- changeset courseflow:loyalty-006-processed-inbound-events

CREATE TABLE IF NOT EXISTS loyalty_processed_inbound_events (
    id UUID PRIMARY KEY,
    source_topic VARCHAR(240) NOT NULL,
    source_event_type VARCHAR(160) NOT NULL,
    event_id VARCHAR(180) NOT NULL,
    aggregate_id VARCHAR(180),
    payload_hash VARCHAR(80) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'PROCESSED',
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_processed_inbound_event UNIQUE (source_event_type, event_id),
    CONSTRAINT chk_loyalty_processed_inbound_status CHECK (status IN ('PROCESSED'))
);

CREATE INDEX IF NOT EXISTS idx_loyalty_processed_inbound_source_time
    ON loyalty_processed_inbound_events (source_event_type, processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_processed_inbound_aggregate
    ON loyalty_processed_inbound_events (aggregate_id, processed_at DESC);
