-- liquibase formatted sql
-- Single consolidated baseline for certificate-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:certificate-001-init
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY,
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    final_grade NUMERIC(8,2) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    status VARCHAR(40) NOT NULL DEFAULT 'ISSUED',
    version BIGINT NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_certificates_student_course_issued
    ON certificates (student_id, course_id)
    WHERE status = 'ISSUED';

CREATE TABLE IF NOT EXISTS certificate_verifications (
    id UUID PRIMARY KEY,
    certificate_id UUID NOT NULL REFERENCES certificates(id),
    verification_code VARCHAR(120) NOT NULL UNIQUE,
    signature VARCHAR(255) NOT NULL,
    public_slug VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS certificate_audit_logs (
    id UUID PRIMARY KEY,
    certificate_id UUID NOT NULL REFERENCES certificates(id),
    action VARCHAR(60) NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
-- merged from 002-processed-events.sql
-- ============================================================
-- changeset courseflow:certificate-002-processed-events
CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    consumer_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:certificate-900-demo-data context=demo
INSERT INTO certificates (id, student_id, course_id, final_grade, status)
VALUES ('c1000000-0000-0000-0000-000000000001', '4', '30000000-0000-0000-0000-000000000001', 85, 'ISSUED')
ON CONFLICT (id) DO NOTHING;

INSERT INTO certificate_verifications (id, certificate_id, verification_code, signature, public_slug)
VALUES ('c2000000-0000-0000-0000-000000000001', 'c1000000-0000-0000-0000-000000000001', 'CF-SE401-DEMO', 'demo-signature', 'cf-se401-demo')
ON CONFLICT (verification_code) DO NOTHING;
