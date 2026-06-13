-- liquibase formatted sql

-- changeset courseflow:course-004-optimistic-lock-columns
-- Runtime upgrade for databases that applied course-003-authoring before optimistic locking
-- columns were introduced. The statements are idempotent so fresh databases remain compatible.
ALTER TABLE courses ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;
ALTER TABLE course_modules ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;
ALTER TABLE course_versions ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;
