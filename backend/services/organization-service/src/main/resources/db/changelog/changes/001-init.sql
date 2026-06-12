-- liquibase formatted sql
-- Single consolidated baseline for organization-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:organization-001-init
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    faculty VARCHAR(255) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS academic_terms (
    id UUID PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'OPEN'
);

CREATE TABLE IF NOT EXISTS course_sections (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    term_id UUID NOT NULL REFERENCES academic_terms(id),
    section_code VARCHAR(32) NOT NULL,
    instructor_id VARCHAR(64) NOT NULL,
    capacity INT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    UNIQUE (course_id, term_id, section_code)
);

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:organization-900-demo-data context=demo
INSERT INTO departments (id, code, name, faculty)
VALUES
  ('20000000-0000-0000-0000-000000000001', 'SE', 'Software Engineering', 'Faculty of Information Technology'),
  ('20000000-0000-0000-0000-000000000002', 'CS', 'Computer Science', 'Faculty of Information Technology')
ON CONFLICT (code) DO NOTHING;

INSERT INTO academic_terms (id, code, name, start_date, end_date)
VALUES
  ('20000000-0000-0000-0000-000000000101', '2026-S1', 'Semester 1 2026', '2026-01-15', '2026-05-30')
ON CONFLICT (code) DO NOTHING;
