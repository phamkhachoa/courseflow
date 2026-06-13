-- liquibase formatted sql

-- changeset courseflow:course-007-module-item-status
-- Keep historical item rows addressable for learner progress while authoring can hide
-- removed draft items through a non-destructive archive state.
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE';

ALTER TABLE course_modules DROP CONSTRAINT IF EXISTS course_modules_course_id_position_key;
ALTER TABLE module_items DROP CONSTRAINT IF EXISTS module_items_module_id_position_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_course_modules_active_position
    ON course_modules(course_id, position)
    WHERE status <> 'ARCHIVED';

CREATE UNIQUE INDEX IF NOT EXISTS uq_module_items_active_position
    ON module_items(module_id, position)
    WHERE status <> 'ARCHIVED';

CREATE INDEX IF NOT EXISTS idx_module_items_module_status_position
    ON module_items(module_id, status, position);
