-- liquibase formatted sql
-- changeset courseflow:loyalty-004-inbound-dead-letters

CREATE TABLE IF NOT EXISTS loyalty_inbound_dead_letters (
    id UUID PRIMARY KEY,
    source_topic VARCHAR(240) NOT NULL,
    dlt_topic VARCHAR(240) NOT NULL,
    consumer_group VARCHAR(160),
    kafka_partition INTEGER NOT NULL,
    kafka_offset BIGINT NOT NULL,
    original_partition INTEGER,
    original_offset BIGINT,
    record_key VARCHAR(512),
    payload TEXT NOT NULL,
    payload_hash VARCHAR(80) NOT NULL,
    exception_class VARCHAR(240),
    exception_message TEXT,
    stacktrace TEXT,
    headers_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(40) NOT NULL DEFAULT 'OPEN',
    replay_attempts INTEGER NOT NULL DEFAULT 0,
    last_replay_error TEXT,
    last_replay_at TIMESTAMPTZ,
    replayed_at TIMESTAMPTZ,
    discarded_at TIMESTAMPTZ,
    resolved_by VARCHAR(160),
    resolution_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_inbound_dlt_location UNIQUE (dlt_topic, kafka_partition, kafka_offset),
    CONSTRAINT chk_loyalty_inbound_dlt_status CHECK (status IN ('OPEN', 'FAILED', 'REPLAYED', 'DISCARDED'))
);

CREATE INDEX IF NOT EXISTS idx_loyalty_inbound_dlt_status_created
    ON loyalty_inbound_dead_letters (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_inbound_dlt_source_created
    ON loyalty_inbound_dead_letters (source_topic, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_inbound_dlt_payload_hash
    ON loyalty_inbound_dead_letters (payload_hash);
