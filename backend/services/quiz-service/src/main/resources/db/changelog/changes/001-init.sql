-- liquibase formatted sql
-- Single consolidated baseline for quiz-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:quiz-001-init
CREATE TABLE IF NOT EXISTS question_banks (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY,
    bank_id UUID NOT NULL REFERENCES question_banks(id),
    type VARCHAR(60) NOT NULL,
    stem TEXT NOT NULL,
    difficulty VARCHAR(40) NOT NULL DEFAULT 'MEDIUM',
    points NUMERIC(8,2) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS question_options (
    id UUID PRIMARY KEY,
    question_id UUID NOT NULL REFERENCES questions(id),
    label VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    correct BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS quizzes (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    open_at TIMESTAMPTZ,
    close_at TIMESTAMPTZ,
    duration_minutes INT NOT NULL,
    attempts_allowed INT NOT NULL DEFAULT 1,
    randomize_questions BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT'
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id UUID PRIMARY KEY,
    quiz_id UUID NOT NULL REFERENCES quizzes(id),
    question_id UUID NOT NULL REFERENCES questions(id),
    points NUMERIC(8,2) NOT NULL,
    position INT NOT NULL,
    UNIQUE (quiz_id, question_id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY,
    quiz_id UUID NOT NULL REFERENCES quizzes(id),
    student_id VARCHAR(64) NOT NULL,
    attempt_no INT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    status VARCHAR(40) NOT NULL DEFAULT 'IN_PROGRESS',
    score NUMERIC(8,2),
    version BIGINT NOT NULL DEFAULT 0,
    UNIQUE (quiz_id, student_id, attempt_no)
);

CREATE TABLE IF NOT EXISTS quiz_answers (
    id UUID PRIMARY KEY,
    attempt_id UUID NOT NULL REFERENCES quiz_attempts(id),
    question_id UUID NOT NULL REFERENCES questions(id),
    answer_payload JSONB NOT NULL,
    score NUMERIC(8,2),
    graded_at TIMESTAMPTZ,
    UNIQUE (attempt_id, question_id)
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

-- ============================================================
-- merged from 002-question-types-scoring.sql
-- ============================================================
-- changeset courseflow:quiz-002-question-types-scoring
--validCheckSum 9:27d799048071269757a6c009c1149504

-- Quizzes: scoring strategy across multiple attempts + time-limit enforcement
ALTER TABLE quizzes
    ADD COLUMN IF NOT EXISTS scoring_method VARCHAR(20) NOT NULL DEFAULT 'HIGHEST',
    ADD COLUMN IF NOT EXISTS time_limit_enforced BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS show_correct_answers BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE quizzes ALTER COLUMN time_limit_enforced SET DEFAULT TRUE;
UPDATE quizzes SET time_limit_enforced = TRUE
WHERE status = 'PUBLISHED' AND time_limit_enforced = FALSE;

-- Questions: store reference answer for non-MCQ types as JSON
--   SHORT_ANSWER : {"answers":["one","two"], "caseSensitive":false}
--   FILL_BLANK   : {"answers":[["a","A"],["b"]]}      (array per blank, any value matches)
--   NUMERICAL    : {"value":3.14, "tolerance":0.01}
--   MATCHING     : {"pairs":{"a":"1","b":"2"}}
--   ESSAY        : {} (manual grading)
ALTER TABLE questions
    ADD COLUMN IF NOT EXISTS correct_answer JSONB,
    ADD COLUMN IF NOT EXISTS feedback TEXT;

-- Question options: per-option weight (partial credit for MULTIPLE_RESPONSE),
-- plus per-option feedback.
ALTER TABLE question_options
    ADD COLUMN IF NOT EXISTS weight NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS feedback TEXT;

-- Quiz answers: separate auto- and manual-grade columns + free-text feedback (for essay grading).
ALTER TABLE quiz_answers
    ADD COLUMN IF NOT EXISTS auto_score NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS manual_score NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS manual_feedback TEXT,
    ADD COLUMN IF NOT EXISTS grader_id VARCHAR(64);

-- Idempotency table (future-proofing for cross-service consumers)
CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    consumer_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 003-attempt-snapshot.sql
-- ============================================================
-- changeset courseflow:quiz-003-attempt-snapshot

-- Quizzes: grace period after the time limit, and option-level shuffle.
ALTER TABLE quizzes
    ADD COLUMN IF NOT EXISTS grace_period_seconds INT NOT NULL DEFAULT 60,
    ADD COLUMN IF NOT EXISTS randomize_options BOOLEAN NOT NULL DEFAULT FALSE;

-- Per-attempt question snapshot (Moodle-style): the full frozen question list (including the
-- shuffled order, points, correct answers and options) is captured at attempt start so that
--   (a) editing a question/answer key mid-flight cannot change an in-progress or graded attempt, and
--   (b) regrades are reproducible against exactly what the student saw.
-- deadline_at is the hard end time (min(started_at + duration, close_at)); auto_submitted marks
-- attempts that were finalized by the sweeper rather than by the student.
ALTER TABLE quiz_attempts
    ADD COLUMN IF NOT EXISTS questions_snapshot JSONB,
    ADD COLUMN IF NOT EXISTS deadline_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS auto_submitted BOOLEAN NOT NULL DEFAULT FALSE;

-- Sweeper lookup: find expired in-progress attempts cheaply.
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_in_progress
    ON quiz_attempts (deadline_at)
    WHERE status = 'IN_PROGRESS';

-- Hot path for the relay and attempt-limit checks.
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox_events (created_at, id)
    WHERE published_at IS NULL;

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:quiz-900-demo-data context=demo
INSERT INTO question_banks (id, course_id, title, created_by)
VALUES ('b1000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Microservice foundations', '2')
ON CONFLICT (id) DO NOTHING;

INSERT INTO questions (id, bank_id, type, stem, difficulty, points)
VALUES
  ('b2000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000001', 'MULTIPLE_CHOICE', 'Which component owns public course search documents?', 'EASY', 10),
  ('b2000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000001', 'TRUE_FALSE', 'A service may query another service database if it knows the connection string.', 'EASY', 10)
ON CONFLICT (id) DO NOTHING;

INSERT INTO question_options (id, question_id, label, content, correct)
VALUES
  ('b2100000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000001', 'A', 'course-service', FALSE),
  ('b2100000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000001', 'B', 'search-service', TRUE),
  ('b2100000-0000-0000-0000-000000000003', 'b2000000-0000-0000-0000-000000000001', 'C', 'analytics-service', FALSE),
  ('b2100000-0000-0000-0000-000000000004', 'b2000000-0000-0000-0000-000000000002', 'TRUE', 'True', FALSE),
  ('b2100000-0000-0000-0000-000000000005', 'b2000000-0000-0000-0000-000000000002', 'FALSE', 'False', TRUE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO quizzes (id, course_id, title, duration_minutes, attempts_allowed, randomize_questions, status)
VALUES ('b3000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Microservice boundaries quiz', 20, 2, TRUE, 'PUBLISHED')
ON CONFLICT (id) DO NOTHING;

INSERT INTO quiz_questions (id, quiz_id, question_id, points, position)
VALUES
  ('b4000000-0000-0000-0000-000000000001', 'b3000000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000001', 10, 1),
  ('b4000000-0000-0000-0000-000000000002', 'b3000000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000002', 10, 2)
ON CONFLICT (quiz_id, question_id) DO NOTHING;
