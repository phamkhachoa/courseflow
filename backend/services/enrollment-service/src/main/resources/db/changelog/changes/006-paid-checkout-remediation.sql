-- liquibase formatted sql
-- changeset courseflow:enrollment-006-paid-checkout-remediation

ALTER TABLE enrollment_checkout_attempts
    DROP CONSTRAINT IF EXISTS chk_enrollment_checkout_attempt_status;

ALTER TABLE enrollment_checkout_attempts
    ADD CONSTRAINT chk_enrollment_checkout_attempt_status CHECK (
        status IN ('STARTED', 'RESERVED', 'ENROLLMENT_CREATED', 'COMMITTING', 'PAYMENT_PENDING',
                   'SUCCEEDED', 'COMMIT_FAILED', 'MANUAL_REVIEW', 'CANCELLED', 'FAILED')
    );

CREATE TABLE IF NOT EXISTS enrollment_orders (
    id UUID PRIMARY KEY,
    enrollment_id UUID NOT NULL REFERENCES enrollments(id),
    checkout_attempt_id UUID REFERENCES enrollment_checkout_attempts(id),
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    status VARCHAR(40) NOT NULL,
    amount NUMERIC(19, 2) NOT NULL,
    currency VARCHAR(12) NOT NULL,
    payment_provider VARCHAR(80),
    payment_reference VARCHAR(180),
    failure_reason TEXT,
    idempotency_key VARCHAR(180),
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_enrollment_order_enrollment UNIQUE (enrollment_id),
    CONSTRAINT chk_enrollment_order_status CHECK (
        status IN ('PAYMENT_PENDING', 'PAID', 'PAYMENT_FAILED', 'EXPIRED', 'MANUAL_REVIEW')
    ),
    CONSTRAINT chk_enrollment_order_amount_non_negative CHECK (amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_enrollment_orders_scope
    ON enrollment_orders (course_id, student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_enrollment_orders_status
    ON enrollment_orders (status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_enrollment_orders_checkout_attempt
    ON enrollment_orders (checkout_attempt_id)
    WHERE checkout_attempt_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS enrollment_remediation_cases (
    id UUID PRIMARY KEY,
    case_type VARCHAR(60) NOT NULL,
    status VARCHAR(40) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    enrollment_id UUID REFERENCES enrollments(id),
    checkout_attempt_id UUID REFERENCES enrollment_checkout_attempts(id),
    promotion_application_id UUID REFERENCES enrollment_promotion_applications(id),
    order_id UUID REFERENCES enrollment_orders(id),
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    assignee_id VARCHAR(80) NOT NULL,
    note TEXT,
    reason_code VARCHAR(120) NOT NULL,
    sla_due_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_enrollment_remediation_case_status CHECK (
        status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')
    )
);

CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_cases_queue
    ON enrollment_remediation_cases (status, sla_due_at, created_at);
CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_cases_scope
    ON enrollment_remediation_cases (course_id, student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_cases_promotion
    ON enrollment_remediation_cases (promotion_application_id)
    WHERE promotion_application_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_cases_order
    ON enrollment_remediation_cases (order_id)
    WHERE order_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS enrollment_remediation_case_actions (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES enrollment_remediation_cases(id) ON DELETE CASCADE,
    action VARCHAR(80) NOT NULL,
    actor_id VARCHAR(80) NOT NULL,
    note TEXT,
    from_status VARCHAR(40),
    to_status VARCHAR(40),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_case_actions_case
    ON enrollment_remediation_case_actions (case_id, created_at ASC);
