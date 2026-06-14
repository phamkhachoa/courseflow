-- liquibase formatted sql
-- Hardening constraints for transaction idempotency and side-effect uniqueness.

-- changeset courseflow:promotion-002-hardening
ALTER TABLE incentive_idempotency_keys
    DROP CONSTRAINT IF EXISTS chk_incentive_idempotency_status;

ALTER TABLE incentive_idempotency_keys
    ADD CONSTRAINT chk_incentive_idempotency_status
    CHECK (status IN ('IN_PROGRESS', 'SUCCEEDED', 'FAILED'));

DELETE FROM incentive_ledger_entries
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY reservation_id, entry_type
                   ORDER BY created_at ASC, id ASC
               ) AS duplicate_rank
        FROM incentive_ledger_entries
        WHERE reservation_id IS NOT NULL
          AND entry_type = 'COMMIT'
    ) ranked
    WHERE duplicate_rank > 1
);

DELETE FROM outbox_events
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY aggregate_id, event_type
                   ORDER BY created_at ASC, id ASC
               ) AS duplicate_rank
        FROM outbox_events
        WHERE aggregate_type = 'incentive-redemption'
          AND event_type = 'incentive.redemption.committed'
    ) ranked
    WHERE duplicate_rank > 1
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_incentive_ledger_commit_reservation
    ON incentive_ledger_entries (reservation_id, entry_type)
    WHERE reservation_id IS NOT NULL AND entry_type = 'COMMIT';

CREATE UNIQUE INDEX IF NOT EXISTS uk_outbox_incentive_redemption_committed
    ON outbox_events (aggregate_id, event_type)
    WHERE aggregate_type = 'incentive-redemption' AND event_type = 'incentive.redemption.committed';
