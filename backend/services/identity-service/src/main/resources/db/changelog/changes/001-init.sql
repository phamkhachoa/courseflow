-- liquibase formatted sql
-- changeset courseflow:identity-001-init splitStatements:false
-- Clean baseline schema for cf_identity. Replaces the older 001/002/003 trio
-- (legacy users.role / user_memberships / role_permissions are gone).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── users ──────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id                   BIGSERIAL    PRIMARY KEY,
    email                VARCHAR(255) NOT NULL,
    email_verified       BOOLEAN      NOT NULL DEFAULT FALSE,
    password_hash        VARCHAR(255) NOT NULL,
    password_changed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    must_change_password BOOLEAN      NOT NULL DEFAULT FALSE,
    full_name            VARCHAR(255) NOT NULL,
    status               VARCHAR(40)  NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SUSPENDED','DEACTIVATED','PENDING_VERIFICATION')),
    failed_login_count   INTEGER      NOT NULL DEFAULT 0,
    locked_until         TIMESTAMPTZ,
    last_login_at        TIMESTAMPTZ,
    mfa_enabled          BOOLEAN      NOT NULL DEFAULT FALSE,
    mfa_secret           VARCHAR(255),
    created_on           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by           VARCHAR(255),
    last_modified_on     TIMESTAMPTZ,
    last_modified_by     VARCHAR(255),
    version              BIGINT       NOT NULL DEFAULT 0
);
-- Case-insensitive uniqueness: matches UserRepository.findByEmailIgnoreCase / existsByEmailIgnoreCase.
CREATE UNIQUE INDEX uq_users_email_ci ON users (LOWER(email));

-- ─── refresh_tokens ─────────────────────────────────────────────────────────
CREATE TABLE refresh_tokens (
    id              BIGSERIAL    PRIMARY KEY,
    user_id         BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ  NOT NULL,
    revoked         BOOLEAN      NOT NULL DEFAULT FALSE,
    revoked_at      TIMESTAMPTZ,
    revoked_reason  VARCHAR(80),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    version         BIGINT       NOT NULL DEFAULT 0
);
-- Hot paths: revoke-by-user and TTL cleanup. Without these the bulk-revoke
-- update and the eventual sweeper would full-scan a fast-growing table.
CREATE INDEX idx_refresh_tokens_user      ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires   ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_user_live ON refresh_tokens(user_id) WHERE revoked = FALSE;

-- ─── permissions ────────────────────────────────────────────────────────────
-- Keep `code` as PK for now (cross-service references use the human-readable code).
-- scope_type tells callers what kind of scope a permission is meaningful at.
CREATE TABLE permissions (
    code        VARCHAR(80)  PRIMARY KEY,             -- resource:action e.g. course:publish
    description VARCHAR(255) NOT NULL,
    category    VARCHAR(80)  NOT NULL DEFAULT 'general',
    scope_type  VARCHAR(40)  NOT NULL DEFAULT 'ANY'
        CHECK (scope_type IN ('ANY','PLATFORM','ORG','COURSE','DEPARTMENT')),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_permissions_category ON permissions(category);

-- ─── roles ──────────────────────────────────────────────────────────────────
-- `is_operator` flags roles allowed to touch /internal and /backoffice surfaces.
-- `rank` is used purely to pick a single "primary role" for the X-User-Role header
-- (higher rank wins). Both are exposed in the JWT so the filter does not need any
-- hardcoded role table.
CREATE TABLE roles (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code           VARCHAR(80)  NOT NULL UNIQUE,
    name           VARCHAR(255) NOT NULL,
    description    TEXT,
    is_system      BOOLEAN      NOT NULL DEFAULT FALSE,
    is_operator    BOOLEAN      NOT NULL DEFAULT FALSE,
    rank           INTEGER      NOT NULL DEFAULT 0,
    parent_role_id UUID         REFERENCES roles(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by     VARCHAR(255),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_by     VARCHAR(255)
);

-- ─── role_permission_grants ─────────────────────────────────────────────────
CREATE TABLE role_permission_grants (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID         NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_code VARCHAR(80)  NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
    effect          VARCHAR(10)  NOT NULL DEFAULT 'ALLOW' CHECK (effect IN ('ALLOW','DENY')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(255),
    UNIQUE (role_id, permission_code)
);
CREATE INDEX idx_rpg_permission ON role_permission_grants(permission_code);

-- ─── user_role_assignments ──────────────────────────────────────────────────
-- Soft-delete via revoked_at so a revoked grant stays auditable. The unique index
-- only applies to live (non-revoked) rows so the same role can be re-granted later.
CREATE TABLE user_role_assignments (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID         NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    scope_type  VARCHAR(40)  NOT NULL DEFAULT 'PLATFORM'
        CHECK (scope_type IN ('PLATFORM','ORG','COURSE','DEPARTMENT')),
    scope_id    VARCHAR(255),
    granted_by  VARCHAR(64),
    granted_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ,
    revoked_by  VARCHAR(64),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uq_user_role_assignment_live
    ON user_role_assignments(user_id, role_id, scope_type, COALESCE(scope_id, ''))
    WHERE revoked_at IS NULL;
CREATE INDEX idx_ura_user  ON user_role_assignments(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_ura_role  ON user_role_assignments(role_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_ura_scope ON user_role_assignments(scope_type, scope_id) WHERE revoked_at IS NULL;

-- ─── seed permissions catalog ───────────────────────────────────────────────
INSERT INTO permissions (code, description, category) VALUES
    ('course:read',       'View course content',                                'course'),
    ('course:author',     'Create and edit course drafts',                      'course'),
    ('course:publish',    'Publish a course',                                   'course'),
    ('quiz:author',       'Create and edit quizzes',                            'quiz'),
    ('quiz:grade',        'Grade quiz attempts',                                'quiz'),
    ('assignment:grade',  'Grade assignment submissions',                       'assignment'),
    ('gradebook:manage',  'Manage gradebook entries and overrides',             'gradebook'),
    ('live:host',         'Host live sessions',                                 'live'),
    ('review:moderate',   'Moderate course reviews',                            'review'),
    ('user:manage',       'Manage users within scope',                          'user'),
    ('user:assign-role',  'Assign or revoke roles to users',                    'user'),
    ('org:manage',        'Manage organization settings',                       'org'),
    ('role:manage',       'Create/edit/delete roles and tune permission grants','platform'),
    ('platform:admin',    'Full platform administration',                       'platform');

-- ─── seed system roles (fixed UUIDs let other migrations reference them) ────
-- Hierarchy: PROFESSOR → INSTRUCTOR, TA → STUDENT.
INSERT INTO roles (id, code, name, description, is_system, is_operator, rank, parent_role_id) VALUES
    ('10000000-0000-4000-8000-000000000001', 'STUDENT',    'Học viên',          'Default learner role',                  TRUE, FALSE,  10, NULL),
    ('10000000-0000-4000-8000-000000000002', 'TA',         'Trợ giảng',         'Teaching assistant; inherits STUDENT',  TRUE, FALSE,  30, '10000000-0000-4000-8000-000000000001'),
    ('10000000-0000-4000-8000-000000000003', 'INSTRUCTOR', 'Giảng viên',        'Course author and teacher',             TRUE, FALSE,  50, NULL),
    ('10000000-0000-4000-8000-000000000004', 'PROFESSOR',  'Giáo sư',           'Legacy alias of INSTRUCTOR',            TRUE, FALSE,  50, '10000000-0000-4000-8000-000000000003'),
    ('10000000-0000-4000-8000-000000000005', 'ORG_ADMIN',  'Quản trị tổ chức',  'Manages users and courses in one org',  TRUE, TRUE,   80, NULL),
    ('10000000-0000-4000-8000-000000000006', 'ADMIN',      'Quản trị hệ thống', 'Full platform administration',          TRUE, TRUE,  100, NULL);

-- ─── seed role → permission grants (ALLOW only) ─────────────────────────────
INSERT INTO role_permission_grants (role_id, permission_code, effect)
SELECT r.id, seed.perm_code, 'ALLOW'
FROM (VALUES
    ('STUDENT',    'course:read'),
    ('TA',         'quiz:grade'),
    ('TA',         'assignment:grade'),
    ('TA',         'review:moderate'),
    ('INSTRUCTOR', 'course:read'),
    ('INSTRUCTOR', 'course:author'),
    ('INSTRUCTOR', 'course:publish'),
    ('INSTRUCTOR', 'quiz:author'),
    ('INSTRUCTOR', 'quiz:grade'),
    ('INSTRUCTOR', 'assignment:grade'),
    ('INSTRUCTOR', 'gradebook:manage'),
    ('INSTRUCTOR', 'live:host'),
    ('INSTRUCTOR', 'review:moderate'),
    ('ORG_ADMIN',  'course:publish'),
    ('ORG_ADMIN',  'user:manage'),
    ('ORG_ADMIN',  'user:assign-role'),
    ('ORG_ADMIN',  'org:manage'),
    ('ORG_ADMIN',  'review:moderate'),
    ('ADMIN',      'platform:admin'),
    ('ADMIN',      'role:manage'),
    ('ADMIN',      'user:assign-role')
) AS seed(role_code, perm_code)
JOIN roles r ON r.code = seed.role_code;
