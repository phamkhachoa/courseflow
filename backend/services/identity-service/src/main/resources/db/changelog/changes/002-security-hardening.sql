-- liquibase formatted sql

-- changeset courseflow:identity-002-security-hardening
-- Security hardening for production identity authority:
-- - access-token revocation by jti and user-wide cutoff
-- - durable audit events for auth and role mutation activity

ALTER TABLE users
    ADD COLUMN access_tokens_valid_after TIMESTAMPTZ;

CREATE TABLE revoked_access_tokens (
    jti          VARCHAR(80)  PRIMARY KEY,
    user_id      BIGINT       REFERENCES users(id) ON DELETE CASCADE,
    expires_at   TIMESTAMPTZ  NOT NULL,
    revoked_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    reason       VARCHAR(80)  NOT NULL
);
CREATE INDEX idx_revoked_access_tokens_user ON revoked_access_tokens(user_id);
CREATE INDEX idx_revoked_access_tokens_expires ON revoked_access_tokens(expires_at);

CREATE TABLE security_audit_logs (
    id          BIGSERIAL    PRIMARY KEY,
    event_type  VARCHAR(80)  NOT NULL,
    user_id     BIGINT       REFERENCES users(id) ON DELETE SET NULL,
    email       VARCHAR(255),
    actor_id    VARCHAR(80),
    success     BOOLEAN      NOT NULL,
    detail      VARCHAR(255),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_security_audit_logs_user_created ON security_audit_logs(user_id, created_at DESC);
CREATE INDEX idx_security_audit_logs_event_created ON security_audit_logs(event_type, created_at DESC);

-- Role assignment mutation is intentionally ADMIN-only in JwtIdentityFilter.
-- Keep the permission catalog honest so ORG_ADMIN does not advertise a capability it cannot use.
DELETE FROM role_permission_grants
WHERE permission_code = 'user:assign-role'
  AND role_id = (SELECT id FROM roles WHERE code = 'ORG_ADMIN');
