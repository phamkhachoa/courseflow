-- liquibase formatted sql
-- Single consolidated baseline for outbox-relay. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:outbox-relay-001-init
CREATE TABLE IF NOT EXISTS relay_checkpoints (
    service_name VARCHAR(120) PRIMARY KEY,
    last_event_id UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 002-dead-letter.sql
-- ============================================================
-- changeset courseflow:outbox-relay-002-dead-letter
-- Records outbox rows the relay gave up on after exhausting its in-memory retry budget.
-- Stored in the relay's OWN database (the relay does not own the producing services' tables,
-- so it must not migrate them). Operators can inspect/replay from here.
CREATE TABLE IF NOT EXISTS relay_dead_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(120) NOT NULL,
    source_event_id UUID NOT NULL,
    event_type VARCHAR(120),
    aggregate_id VARCHAR(255),
    payload TEXT,
    attempts INT NOT NULL,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (service_name, source_event_id)
);
