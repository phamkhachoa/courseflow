-- liquibase formatted sql

-- changeset courseflow:notification-003-delivery-retry
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS delivery_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_delivery_attempt_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_notifications_delivery_retry
    ON notifications(delivery_status, delivery_attempts, created_at)
    WHERE delivery_status = 'FAILED';
