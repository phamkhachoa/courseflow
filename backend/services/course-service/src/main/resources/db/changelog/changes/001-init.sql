-- liquibase formatted sql
-- Single consolidated baseline for course-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:course-001-init
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    department_id UUID NOT NULL,
    owner_id VARCHAR(64) NOT NULL,
    level VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_materials (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id),
    title VARCHAR(255) NOT NULL,
    material_type VARCHAR(40) NOT NULL,
    media_id UUID,
    position INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(120) NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox_events (created_at, id)
    WHERE published_at IS NULL;

-- ============================================================
-- merged from 002-course-modules.sql
-- ============================================================
-- changeset courseflow:course-002-course-modules
--validCheckSum 9:bfe4d8065e970716ed34a1be42e26ed0
CREATE TABLE IF NOT EXISTS course_modules (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    position INT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (course_id, position)
);

CREATE TABLE IF NOT EXISTS module_items (
    id UUID PRIMARY KEY,
    module_id UUID NOT NULL REFERENCES course_modules(id),
    item_type VARCHAR(60) NOT NULL,
    item_id VARCHAR(120) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    video_media_id UUID,
    document_media_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_url TEXT,
    estimated_minutes INT,
    position INT NOT NULL,
    required BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (module_id, position)
);

-- changeset courseflow:course-004-rich-lesson-items
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS video_media_id UUID;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS document_media_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS content_url TEXT;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS estimated_minutes INT;

CREATE TABLE IF NOT EXISTS module_prerequisites (
    id UUID PRIMARY KEY,
    module_id UUID NOT NULL REFERENCES course_modules(id),
    required_module_id UUID NOT NULL REFERENCES course_modules(id),
    rule_type VARCHAR(60) NOT NULL
);

CREATE TABLE IF NOT EXISTS learner_module_progress (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id),
    module_id UUID NOT NULL REFERENCES course_modules(id),
    student_id VARCHAR(64) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'NOT_STARTED',
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (module_id, student_id)
);

-- ============================================================
-- merged from 003-authoring.sql
-- ============================================================
-- changeset courseflow:course-003-authoring
--validCheckSum 9:c24df443d29fa2a22bacaf2bfa99668c
-- Instructor authoring: draft versions, review workflow and curriculum editing support.

-- Snapshot of a course's curriculum at a point in time. Lets instructors keep a published
-- version live while editing the next draft, and supports rollback.
CREATE TABLE IF NOT EXISTS course_versions (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id),
    version_no INT NOT NULL,
    state VARCHAR(40) NOT NULL DEFAULT 'DRAFT', -- DRAFT, IN_REVIEW, PUBLISHED, ARCHIVED
    snapshot JSONB,                              -- frozen curriculum payload for PUBLISHED versions
    created_by VARCHAR(64) NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    UNIQUE (course_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_course_versions_course ON course_versions(course_id);

-- Track which version is the working draft and which is live on the course row.
ALTER TABLE courses ADD COLUMN IF NOT EXISTS current_version_no INT NOT NULL DEFAULT 1;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS published_version_no INT;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS review_state VARCHAR(40) NOT NULL DEFAULT 'DRAFT'; -- DRAFT, IN_REVIEW, APPROVED, REJECTED
ALTER TABLE courses ADD COLUMN IF NOT EXISTS last_authored_by VARCHAR(64);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE courses ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;
ALTER TABLE course_modules ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;
ALTER TABLE course_versions ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:course-900-demo-data context=demo
INSERT INTO courses (id, code, title, slug, summary, department_id, owner_id, level, status)
VALUES
  ('30000000-0000-0000-0000-000000000001', 'SE401', 'Production Microservices with Spring Boot', 'production-microservices-spring-boot', 'Build a production-minded LMS backend with domain services, Kafka, outbox, search and analytics.', '20000000-0000-0000-0000-000000000001', '2', 'ADVANCED', 'PUBLISHED')
ON CONFLICT (code) DO NOTHING;

INSERT INTO course_materials (id, course_id, title, material_type, position)
VALUES
  ('30000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000000001', 'Architecture overview', 'ARTICLE', 1),
  ('30000000-0000-0000-0000-000000000102', '30000000-0000-0000-0000-000000000001', 'Outbox and CDC lab', 'LAB', 2)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- merged from 901-demo-course-modules.sql
-- ============================================================
-- changeset courseflow:course-901-demo-course-modules context=demo
--validCheckSum 9:966facbbf2fc86291e75aa08f06c1fba
INSERT INTO course_modules (id, course_id, title, description, position, status)
VALUES
  ('30000000-0000-0000-0000-000000001001', '30000000-0000-0000-0000-000000000001', 'Module 1 - Architecture foundation', 'Learn service ownership, API boundaries and local infra.', 1, 'PUBLISHED'),
  ('30000000-0000-0000-0000-000000001002', '30000000-0000-0000-0000-000000000001', 'Module 2 - Event reliability', 'Practice outbox, dedup, CDC and analytics events.', 2, 'PUBLISHED')
ON CONFLICT (course_id, position) DO NOTHING;

INSERT INTO module_items (id, module_id, item_type, item_id, title, description, estimated_minutes, position, required)
VALUES
  ('30000000-0000-0000-0000-000000002001', '30000000-0000-0000-0000-000000001001', 'LESSON', '30000000-0000-0000-0000-000000000101', 'Read architecture overview', 'Review the architecture guide and identify service ownership boundaries.', 25, 1, TRUE),
  ('30000000-0000-0000-0000-000000002002', '30000000-0000-0000-0000-000000001001', 'ASSIGNMENT', '50000000-0000-0000-0000-000000000001', 'Build service skeleton', 'Implement the first service skeleton and submit the API contract.', 60, 2, TRUE),
  ('30000000-0000-0000-0000-000000002003', '30000000-0000-0000-0000-000000001002', 'LESSON', '30000000-0000-0000-0000-000000000102', 'Run outbox and CDC lab', 'Practice outbox publishing, replay safety and analytics event consumption.', 40, 1, TRUE)
ON CONFLICT (module_id, position) DO NOTHING;

INSERT INTO module_prerequisites (id, module_id, required_module_id, rule_type)
VALUES
  ('30000000-0000-0000-0000-000000003001', '30000000-0000-0000-0000-000000001002', '30000000-0000-0000-0000-000000001001', 'MODULE_COMPLETED')
ON CONFLICT (id) DO NOTHING;
