-- liquibase formatted sql

-- changeset courseflow:identity-003-email-verification
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id           UUID         PRIMARY KEY,
    user_id      BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(128) NOT NULL UNIQUE,
    expires_at   TIMESTAMPTZ  NOT NULL,
    consumed_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user_live
    ON email_verification_tokens(user_id, expires_at)
    WHERE consumed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires
    ON email_verification_tokens(expires_at);

CREATE TABLE IF NOT EXISTS outbox_events (
    id             UUID         PRIMARY KEY,
    aggregate_id   VARCHAR(120) NOT NULL,
    aggregate_type VARCHAR(120) NOT NULL,
    event_type     VARCHAR(120) NOT NULL,
    payload        JSONB        NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_identity_outbox_unpublished
    ON outbox_events(created_at, id)
    WHERE published_at IS NULL;
