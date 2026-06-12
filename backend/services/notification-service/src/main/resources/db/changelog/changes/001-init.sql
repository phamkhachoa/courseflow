-- liquibase formatted sql
-- Single consolidated baseline for notification-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:notification-001-init
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    notification_type VARCHAR(80) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    channel VARCHAR(40) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (user_id, channel)
);

CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    consumer_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:notification-900-demo-data context=demo
INSERT INTO notifications (id, user_id, notification_type, title, body)
VALUES
  ('90000000-0000-0000-0000-000000000001', '4', 'ANNOUNCEMENT', 'Welcome to CourseFlow v2', 'You have a new course announcement.')
ON CONFLICT (id) DO NOTHING;
