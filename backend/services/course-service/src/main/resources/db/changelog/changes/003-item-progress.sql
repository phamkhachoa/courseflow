-- liquibase formatted sql

-- changeset courseflow:course-003-item-progress
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS learner_item_progress (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id),
    module_id UUID NOT NULL REFERENCES course_modules(id),
    item_id UUID NOT NULL REFERENCES module_items(id),
    student_id VARCHAR(64) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'NOT_STARTED',
    progress_type VARCHAR(60) NOT NULL DEFAULT 'MANUAL',
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (item_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_learner_item_progress_course_student
    ON learner_item_progress (course_id, student_id);

CREATE INDEX IF NOT EXISTS idx_learner_item_progress_module_student
    ON learner_item_progress (module_id, student_id);

-- Preserve existing module-level progress by treating every required item in a
-- completed module as completed. This keeps current demo/user progress stable
-- while the product moves to item-level completion.
INSERT INTO learner_item_progress (
    id,
    course_id,
    module_id,
    item_id,
    student_id,
    status,
    progress_type,
    completed_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    p.course_id,
    i.module_id,
    i.id,
    p.student_id,
    'COMPLETED',
    'MODULE_BACKFILL',
    p.completed_at,
    COALESCE(p.completed_at, p.updated_at, NOW())
FROM learner_module_progress p
JOIN module_items i ON i.module_id = p.module_id
WHERE p.status = 'COMPLETED'
  AND i.required = TRUE
ON CONFLICT (item_id, student_id) DO NOTHING;
