-- liquibase formatted sql

-- changeset courseflow:outbox-relay-003-dead-letter-replay
ALTER TABLE relay_dead_letters
    ADD COLUMN IF NOT EXISTS status VARCHAR(24) NOT NULL DEFAULT 'OPEN',
    ADD COLUMN IF NOT EXISTS replay_attempts INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_replay_error TEXT,
    ADD COLUMN IF NOT EXISTS last_replay_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS replayed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS discarded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(255),
    ADD COLUMN IF NOT EXISTS resolution_note TEXT,
    ADD COLUMN IF NOT EXISTS locked_by VARCHAR(120),
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS payload_hash VARCHAR(80);

CREATE INDEX IF NOT EXISTS idx_relay_dead_letters_status_created
    ON relay_dead_letters (status, created_at);

CREATE INDEX IF NOT EXISTS idx_relay_dead_letters_service_event_status
    ON relay_dead_letters (service_name, event_type, status);

CREATE TABLE IF NOT EXISTS relay_delivery_states (
    service_name VARCHAR(120) NOT NULL,
    source_event_id UUID NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    first_failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_error TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'FAILING',
    PRIMARY KEY (service_name, source_event_id)
);

CREATE TABLE IF NOT EXISTS relay_operator_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(160) NOT NULL,
    action VARCHAR(32) NOT NULL,
    dead_letter_id UUID NOT NULL REFERENCES relay_dead_letters(id),
    request_hash VARCHAR(80) NOT NULL,
    response_json TEXT NOT NULL DEFAULT '{}',
    status VARCHAR(24) NOT NULL,
    actor_id VARCHAR(255),
    correlation_id VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE (idempotency_key, action, dead_letter_id)
);
