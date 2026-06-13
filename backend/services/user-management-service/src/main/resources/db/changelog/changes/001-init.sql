-- liquibase formatted sql
-- changeset courseflow:user-management-001-init splitStatements:false

CREATE TABLE user_profiles (
    user_id       BIGINT       PRIMARY KEY,
    display_name  VARCHAR(255) NOT NULL,
    avatar_url    TEXT,
    bio           TEXT,
    locale        VARCHAR(20)  NOT NULL DEFAULT 'vi-VN',
    timezone      VARCHAR(80)  NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    visibility    VARCHAR(40)  NOT NULL DEFAULT 'PRIVATE'
        CHECK (visibility IN ('PUBLIC','PRIVATE','ORG')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_user_profiles_display_name ON user_profiles(LOWER(display_name));
CREATE INDEX idx_user_profiles_visibility ON user_profiles(visibility);

CREATE TABLE user_profile_audit_logs (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    actor_id    VARCHAR(80),
    action      VARCHAR(80)  NOT NULL,
    detail      VARCHAR(255),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_user_profile_audit_user_created ON user_profile_audit_logs(user_id, created_at DESC);
