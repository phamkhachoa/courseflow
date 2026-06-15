-- liquibase formatted sql

-- changeset courseflow:loyalty-010-inbound-dlt-maker-checker
CREATE TABLE IF NOT EXISTS loyalty_inbound_dead_letter_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dead_letter_id UUID NOT NULL REFERENCES loyalty_inbound_dead_letters(id),
    action VARCHAR(32) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    reason TEXT NOT NULL,
    evidence_reference TEXT NOT NULL,
    threshold_policy VARCHAR(120) NOT NULL,
    payload_hash VARCHAR(80) NOT NULL,
    request_hash VARCHAR(80) NOT NULL,
    requested_by VARCHAR(160) NOT NULL,
    reviewed_by VARCHAR(160),
    review_note TEXT,
    executed_by VARCHAR(160),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CHECK (action IN ('REPLAY', 'DISCARD')),
    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_loyalty_inbound_dlt_approval_active
    ON loyalty_inbound_dead_letter_approvals (dead_letter_id, action, request_hash)
    WHERE status IN ('PENDING', 'APPROVED', 'EXECUTED');

CREATE INDEX IF NOT EXISTS idx_loyalty_inbound_dlt_approval_status
    ON loyalty_inbound_dead_letter_approvals (dead_letter_id, status, requested_at DESC);
