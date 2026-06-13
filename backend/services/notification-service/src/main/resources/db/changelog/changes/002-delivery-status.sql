-- liquibase formatted sql

-- changeset courseflow:notification-002-delivery-status
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delivery_error VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_notifications_delivery_status
    ON notifications(delivery_status, created_at DESC);
