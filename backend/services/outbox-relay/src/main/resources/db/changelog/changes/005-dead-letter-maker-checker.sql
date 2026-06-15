-- liquibase formatted sql

-- changeset courseflow:outbox-relay-005-dead-letter-maker-checker
CREATE TABLE IF NOT EXISTS relay_dead_letter_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dead_letter_id UUID NOT NULL REFERENCES relay_dead_letters(id),
    action VARCHAR(32) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    reason TEXT NOT NULL,
    evidence_reference TEXT NOT NULL,
    threshold_policy VARCHAR(120) NOT NULL,
    payload_hash VARCHAR(80) NOT NULL,
    request_hash VARCHAR(80) NOT NULL,
    requested_by VARCHAR(255) NOT NULL,
    reviewed_by VARCHAR(255),
    review_note TEXT,
    executed_by VARCHAR(255),
    execution_idempotency_key VARCHAR(160),
    correlation_id VARCHAR(160),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    CHECK (action IN ('REPLAY', 'DISCARD')),
    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_relay_dlt_approval_active_request
    ON relay_dead_letter_approvals (dead_letter_id, action, request_hash)
    WHERE status IN ('PENDING', 'APPROVED', 'EXECUTED');

CREATE INDEX IF NOT EXISTS idx_relay_dlt_approval_dead_letter_status
    ON relay_dead_letter_approvals (dead_letter_id, status, requested_at DESC);
