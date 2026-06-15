-- liquibase formatted sql

-- changeset courseflow:notification-004-delivery-dispatching-retry-index
DROP INDEX IF EXISTS idx_notifications_delivery_retry;

CREATE INDEX IF NOT EXISTS idx_notifications_delivery_retry
    ON notifications(delivery_status, delivery_attempts, last_delivery_attempt_at, created_at)
    WHERE delivery_status IN ('FAILED', 'DISPATCHING');
