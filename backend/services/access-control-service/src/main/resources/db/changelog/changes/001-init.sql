-- liquibase formatted sql
-- changeset courseflow:access-control-001-init splitStatements:false

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE access_users (
    id                 BIGINT      PRIMARY KEY,
    email              VARCHAR(255),
    status             VARCHAR(40) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SUSPENDED','DEACTIVATED','PENDING_VERIFICATION')),
    tokens_valid_after TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uq_access_users_email_ci ON access_users (LOWER(email)) WHERE email IS NOT NULL;

CREATE TABLE external_identity_links (
    id                     BIGSERIAL    PRIMARY KEY,
    user_id                BIGINT       NOT NULL REFERENCES access_users(id) ON DELETE CASCADE,
    provider               VARCHAR(80)  NOT NULL DEFAULT 'keycloak',
    issuer                 VARCHAR(255) NOT NULL,
    subject                VARCHAR(255) NOT NULL,
    email_at_link          VARCHAR(255),
    email_verified_at_link BOOLEAN,
    status                 VARCHAR(40)  NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','DISABLED')),
    linked_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen_at           TIMESTAMPTZ,
    UNIQUE (issuer, subject)
);
CREATE INDEX idx_external_identity_links_user ON external_identity_links(user_id);

CREATE TABLE permissions (
    code        VARCHAR(80)  PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    category    VARCHAR(80)  NOT NULL DEFAULT 'general',
    scope_type  VARCHAR(40)  NOT NULL DEFAULT 'ANY'
        CHECK (scope_type IN ('ANY','PLATFORM','ORG','COURSE','DEPARTMENT','SECTION')),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_permissions_category ON permissions(category);

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

CREATE TABLE role_permission_grants (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID         NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_code VARCHAR(80)  NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
    effect          VARCHAR(10)  NOT NULL DEFAULT 'ALLOW' CHECK (effect IN ('ALLOW','DENY')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(255),
    UNIQUE (role_id, permission_code)
);
CREATE INDEX idx_access_rpg_permission ON role_permission_grants(permission_code);

CREATE TABLE user_role_assignments (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL REFERENCES access_users(id) ON DELETE CASCADE,
    role_id     UUID         NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    scope_type  VARCHAR(40)  NOT NULL DEFAULT 'PLATFORM'
        CHECK (scope_type IN ('PLATFORM','ORG','COURSE','DEPARTMENT','SECTION')),
    scope_id    VARCHAR(255),
    granted_by  VARCHAR(80),
    granted_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ,
    revoked_by  VARCHAR(80),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uq_access_user_role_assignment_live
    ON user_role_assignments(user_id, role_id, scope_type, COALESCE(scope_id, ''))
    WHERE revoked_at IS NULL;
CREATE INDEX idx_access_ura_user  ON user_role_assignments(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_access_ura_scope ON user_role_assignments(scope_type, scope_id) WHERE revoked_at IS NULL;

CREATE TABLE access_control_audit_logs (
    id          BIGSERIAL    PRIMARY KEY,
    event_type  VARCHAR(80)  NOT NULL,
    user_id     BIGINT       REFERENCES access_users(id) ON DELETE SET NULL,
    actor_id    VARCHAR(80),
    success     BOOLEAN      NOT NULL,
    detail      VARCHAR(255),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_access_audit_user_created ON access_control_audit_logs(user_id, created_at DESC);
CREATE INDEX idx_access_audit_event_created ON access_control_audit_logs(event_type, created_at DESC);

INSERT INTO permissions (code, description, category, scope_type) VALUES
    ('course:read',       'View course content',                                 'course',      'COURSE'),
    ('course:author',     'Create and edit course drafts',                       'course',      'DEPARTMENT'),
    ('course:publish',    'Publish a course',                                    'course',      'DEPARTMENT'),
    ('quiz:author',       'Create and edit quizzes',                             'quiz',        'COURSE'),
    ('quiz:grade',        'Grade quiz attempts',                                 'quiz',        'COURSE'),
    ('assignment:grade',  'Grade assignment submissions',                        'assignment',  'COURSE'),
    ('gradebook:manage',  'Manage gradebook entries and overrides',              'gradebook',   'COURSE'),
    ('live:host',         'Host live sessions',                                  'live',        'COURSE'),
    ('review:moderate',   'Moderate course reviews',                             'review',      'COURSE'),
    ('user:manage',       'Manage users within scope',                           'user',        'ORG'),
    ('user:assign-role',  'Assign or revoke CourseFlow product roles',           'user',        'ORG'),
    ('org:manage',        'Manage organization settings',                        'org',         'ORG'),
    ('role:manage',       'Create/edit/delete roles and permission grants',      'platform',    'PLATFORM'),
    ('platform:admin',    'Full platform administration',                        'platform',    'PLATFORM')
ON CONFLICT (code) DO NOTHING;

INSERT INTO roles (id, code, name, description, is_system, is_operator, rank, parent_role_id) VALUES
    ('10000000-0000-4000-8000-000000000001', 'STUDENT',    'Học viên',          'Default learner role',                  TRUE, FALSE,  10, NULL),
    ('10000000-0000-4000-8000-000000000002', 'TA',         'Trợ giảng',         'Teaching assistant; inherits STUDENT',  TRUE, FALSE,  30, '10000000-0000-4000-8000-000000000001'),
    ('10000000-0000-4000-8000-000000000003', 'INSTRUCTOR', 'Giảng viên',        'Course author and teacher',             TRUE, FALSE,  50, NULL),
    ('10000000-0000-4000-8000-000000000004', 'PROFESSOR',  'Giáo sư',           'Legacy alias of INSTRUCTOR',            TRUE, FALSE,  50, '10000000-0000-4000-8000-000000000003'),
    ('10000000-0000-4000-8000-000000000005', 'ORG_ADMIN',  'Quản trị tổ chức',  'Manages users and courses in one org',  TRUE, TRUE,   80, NULL),
    ('10000000-0000-4000-8000-000000000006', 'ADMIN',      'Quản trị hệ thống', 'Full platform administration',          TRUE, TRUE,  100, NULL)
ON CONFLICT (code) DO NOTHING;

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
    ('ORG_ADMIN',  'org:manage'),
    ('ORG_ADMIN',  'review:moderate'),
    ('ADMIN',      'platform:admin'),
    ('ADMIN',      'role:manage'),
    ('ADMIN',      'user:assign-role')
) AS seed(role_code, perm_code)
JOIN roles r ON r.code = seed.role_code
ON CONFLICT (role_id, permission_code) DO NOTHING;
