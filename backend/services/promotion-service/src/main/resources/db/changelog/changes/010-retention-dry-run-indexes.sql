-- liquibase formatted sql

-- changeset courseflow:promotion-010-retention-dry-run-indexes
CREATE INDEX IF NOT EXISTS idx_incentive_idempotency_scope_expiry
    ON incentive_idempotency_keys (tenant_id, application_id, expires_at);

CREATE INDEX IF NOT EXISTS idx_outbox_published_retention
    ON outbox_events (published_at, id)
    WHERE published_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_incentive_reservations_terminal_retention
    ON incentive_reservations (tenant_id, application_id, status, expires_at, cancelled_at)
    WHERE status IN ('EXPIRED', 'CANCELLED');
