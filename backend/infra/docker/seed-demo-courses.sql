\set ON_ERROR_STOP on

-- CourseFlow local demo catalog.
-- Safe to run multiple times after the local Compose databases have been created.

\connect cf_organization

INSERT INTO departments (id, code, name, faculty, status)
VALUES
    ('20000000-0000-0000-0000-000000000001', 'SE', 'Software Engineering', 'Faculty of Information Technology', 'ACTIVE'),
    ('20000000-0000-0000-0000-000000000002', 'CS', 'Computer Science', 'Faculty of Information Technology', 'ACTIVE'),
    ('20000000-0000-0000-0000-000000000003', 'AI', 'AI and Data Products', 'Faculty of Information Technology', 'ACTIVE')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    faculty = EXCLUDED.faculty,
    status = EXCLUDED.status;

INSERT INTO academic_terms (id, code, name, start_date, end_date, status)
VALUES
    ('20000000-0000-0000-0000-000000000101', '2026-S1', 'Semester 1 2026', '2026-01-15', '2026-05-30', 'OPEN'),
    ('20000000-0000-0000-0000-000000000102', '2026-S2', 'Semester 2 2026', '2026-08-01', '2026-12-15', 'OPEN')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date,
    status = EXCLUDED.status;

INSERT INTO course_sections (id, course_id, term_id, section_code, instructor_id, capacity, status)
VALUES
    ('21000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000102', 'SE401-A', '2', 40, 'OPEN'),
    ('21000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000102', 'AI210-A', '2', 35, 'OPEN'),
    ('21000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000102', 'DE320-A', '2', 30, 'OPEN'),
    ('21000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000102', 'LX120-A', '2', 45, 'OPEN')
ON CONFLICT (course_id, term_id, section_code) DO UPDATE SET
    instructor_id = EXCLUDED.instructor_id,
    capacity = EXCLUDED.capacity,
    status = EXCLUDED.status;

\connect cf_course

INSERT INTO courses (
    id, code, title, slug, summary, department_id, owner_id, level, status,
    current_version_no, review_state, last_authored_by, created_at, updated_at
)
VALUES
    (
        '30000000-0000-0000-0000-000000000001',
        'SE401',
        'Production Microservices with Spring Boot',
        'production-microservices-spring-boot',
        'Build a production-minded LMS backend with Spring Boot, PostgreSQL, Kafka, outbox relay, search, analytics, security hardening and local Docker cluster operations.',
        '20000000-0000-0000-0000-000000000001',
        '2',
        'ADVANCED',
        'PUBLISHED',
        2,
        'APPROVED',
        '2',
        NOW() - INTERVAL '45 days',
        NOW()
    ),
    (
        '30000000-0000-0000-0000-000000000002',
        'AI210',
        'Applied AI Product Engineering',
        'applied-ai-product-engineering',
        'Design, evaluate and ship AI features responsibly: prompt workflows, retrieval patterns, model evaluation, guardrails, UX instrumentation and production release checklists.',
        '20000000-0000-0000-0000-000000000003',
        '2',
        'INTERMEDIATE',
        'PUBLISHED',
        1,
        'APPROVED',
        '2',
        NOW() - INTERVAL '30 days',
        NOW()
    ),
    (
        '30000000-0000-0000-0000-000000000003',
        'DE320',
        'Data Engineering on Kubernetes',
        'data-engineering-on-kubernetes',
        'Operate modern data pipelines with containers, Airflow-style orchestration, streaming ingestion, data quality gates, observability and cost-aware Kubernetes deployments.',
        '20000000-0000-0000-0000-000000000002',
        '2',
        'ADVANCED',
        'PUBLISHED',
        1,
        'APPROVED',
        '2',
        NOW() - INTERVAL '18 days',
        NOW()
    ),
    (
        '30000000-0000-0000-0000-000000000004',
        'LX120',
        'Learning Experience Design Studio',
        'learning-experience-design-studio',
        'Create a complete online course experience: learner personas, outcome maps, video lesson planning, assessment design, feedback loops and accessibility-first UI review.',
        '20000000-0000-0000-0000-000000000001',
        '2',
        'BEGINNER',
        'PUBLISHED',
        1,
        'APPROVED',
        '2',
        NOW() - INTERVAL '12 days',
        NOW()
    )
ON CONFLICT (code) DO UPDATE SET
    title = EXCLUDED.title,
    slug = EXCLUDED.slug,
    summary = EXCLUDED.summary,
    department_id = EXCLUDED.department_id,
    owner_id = EXCLUDED.owner_id,
    level = EXCLUDED.level,
    status = EXCLUDED.status,
    current_version_no = EXCLUDED.current_version_no,
    review_state = EXCLUDED.review_state,
    last_authored_by = EXCLUDED.last_authored_by,
    updated_at = NOW();

INSERT INTO course_materials (id, course_id, title, material_type, media_id, position)
VALUES
    ('32000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000000001', 'Course cover: production service map', 'IMAGE', '91000000-0000-0000-0000-000000000101', 0),
    ('32000000-0000-0000-0000-000000000102', '30000000-0000-0000-0000-000000000001', 'Welcome video: service boundaries in practice', 'VIDEO', '92000000-0000-0000-0000-000000000101', 1),
    ('32000000-0000-0000-0000-000000000103', '30000000-0000-0000-0000-000000000001', 'Architecture workbook', 'PDF', '91000000-0000-0000-0000-000000000301', 2),
    ('32000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000002', 'Course cover: AI product canvas', 'IMAGE', '91000000-0000-0000-0000-000000000102', 0),
    ('32000000-0000-0000-0000-000000000202', '30000000-0000-0000-0000-000000000002', 'Welcome video: AI feature discovery', 'VIDEO', '92000000-0000-0000-0000-000000000102', 1),
    ('32000000-0000-0000-0000-000000000301', '30000000-0000-0000-0000-000000000003', 'Course cover: data platform topology', 'IMAGE', '91000000-0000-0000-0000-000000000103', 0),
    ('32000000-0000-0000-0000-000000000302', '30000000-0000-0000-0000-000000000003', 'Welcome video: streaming pipeline walkthrough', 'VIDEO', '92000000-0000-0000-0000-000000000103', 1),
    ('32000000-0000-0000-0000-000000000401', '30000000-0000-0000-0000-000000000004', 'Course cover: learning journey map', 'IMAGE', '91000000-0000-0000-0000-000000000104', 0),
    ('32000000-0000-0000-0000-000000000402', '30000000-0000-0000-0000-000000000004', 'Welcome video: designing for online learners', 'VIDEO', '92000000-0000-0000-0000-000000000104', 1)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    material_type = EXCLUDED.material_type,
    media_id = EXCLUDED.media_id,
    position = EXCLUDED.position;

INSERT INTO course_modules (id, course_id, title, description, position, status)
VALUES
    ('30000000-0000-0000-0000-000000001001', '30000000-0000-0000-0000-000000000001', 'Architecture Foundation', 'Map identity, course, enrollment, media, quiz and analytics boundaries before writing code.', 1, 'PUBLISHED'),
    ('30000000-0000-0000-0000-000000001002', '30000000-0000-0000-0000-000000000001', 'Reliable Events and Outbox', 'Implement transactional outbox, relay checkpoints, replay safety and observability.', 2, 'PUBLISHED'),
    ('31000000-0000-0000-0000-000000000103', '30000000-0000-0000-0000-000000000001', 'Production Readiness Review', 'Run security, test, performance and deployment checklists before release.', 3, 'PUBLISHED'),
    ('31000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000002', 'AI Feature Discovery', 'Turn user jobs, risk areas and product constraints into an AI feature brief.', 1, 'PUBLISHED'),
    ('31000000-0000-0000-0000-000000000202', '30000000-0000-0000-0000-000000000002', 'Retrieval and Evaluation', 'Build a retrieval workflow, define offline evals and measure failure modes.', 2, 'PUBLISHED'),
    ('31000000-0000-0000-0000-000000000301', '30000000-0000-0000-0000-000000000003', 'Containerized Pipelines', 'Package ingestion and transformation jobs with reproducible local environments.', 1, 'PUBLISHED'),
    ('31000000-0000-0000-0000-000000000302', '30000000-0000-0000-0000-000000000003', 'Streaming Reliability', 'Add schema contracts, retry semantics, watermarking and pipeline dashboards.', 2, 'PUBLISHED'),
    ('31000000-0000-0000-0000-000000000401', '30000000-0000-0000-0000-000000000004', 'Course Storyboard', 'Design outcomes, lesson arcs, video scripts and accessibility review points.', 1, 'PUBLISHED'),
    ('31000000-0000-0000-0000-000000000402', '30000000-0000-0000-0000-000000000004', 'Assessment and Feedback', 'Create rubrics, quiz strategies and instructor feedback loops.', 2, 'PUBLISHED')
ON CONFLICT (course_id, position) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    status = EXCLUDED.status;

INSERT INTO module_items (id, module_id, item_type, item_id, title, position, required)
VALUES
    ('33000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000001001', 'VIDEO', '92000000-0000-0000-0000-000000000101', 'Watch: service boundaries in practice', 1, TRUE),
    ('33000000-0000-0000-0000-000000000102', '30000000-0000-0000-0000-000000001001', 'MATERIAL', '32000000-0000-0000-0000-000000000103', 'Read: architecture workbook', 2, TRUE),
    ('33000000-0000-0000-0000-000000000103', '30000000-0000-0000-0000-000000001002', 'ASSIGNMENT', '50000000-0000-0000-0000-000000000001', 'Outbox Relay Design Review', 1, TRUE),
    ('33000000-0000-0000-0000-000000000104', '31000000-0000-0000-0000-000000000103', 'QUIZ', 'b3000000-0000-0000-0000-000000000001', 'Quiz: microservice boundaries', 1, TRUE),
    ('33000000-0000-0000-0000-000000000201', '31000000-0000-0000-0000-000000000201', 'VIDEO', '92000000-0000-0000-0000-000000000102', 'Watch: AI feature discovery', 1, TRUE),
    ('33000000-0000-0000-0000-000000000202', '31000000-0000-0000-0000-000000000202', 'ASSIGNMENT', '50000000-0000-0000-0000-000000000002', 'Lab: create an evaluation plan', 1, TRUE),
    ('33000000-0000-0000-0000-000000000301', '31000000-0000-0000-0000-000000000301', 'VIDEO', '92000000-0000-0000-0000-000000000103', 'Watch: streaming pipeline walkthrough', 1, TRUE),
    ('33000000-0000-0000-0000-000000000302', '31000000-0000-0000-0000-000000000302', 'QUIZ', 'b3000000-0000-0000-0000-000000000003', 'Quiz: data reliability', 1, TRUE),
    ('33000000-0000-0000-0000-000000000401', '31000000-0000-0000-0000-000000000401', 'VIDEO', '92000000-0000-0000-0000-000000000104', 'Watch: designing for online learners', 1, TRUE),
    ('33000000-0000-0000-0000-000000000402', '31000000-0000-0000-0000-000000000402', 'ASSIGNMENT', '50000000-0000-0000-0000-000000000004', 'Studio: build a lesson storyboard', 1, TRUE)
ON CONFLICT (module_id, position) DO UPDATE SET
    item_type = EXCLUDED.item_type,
    item_id = EXCLUDED.item_id,
    title = EXCLUDED.title,
    required = EXCLUDED.required;

WITH published_course_snapshots AS (
    SELECT
        c.id AS course_id,
        c.current_version_no AS version_no,
        c.owner_id AS created_by,
        COALESCE((
            SELECT jsonb_agg(
                jsonb_build_object(
                    'moduleId', m.id::text,
                    'title', m.title,
                    'description', m.description,
                    'position', m.position,
                    'status', m.status,
                    'items', COALESCE((
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'itemId', i.id::text,
                                'itemType', i.item_type,
                                'refId', i.item_id,
                                'title', i.title,
                                'description', i.description,
                                'videoMediaId', CASE
                                    WHEN UPPER(i.item_type) = 'VIDEO' THEN COALESCE(i.video_media_id::text, i.item_id)
                                    ELSE i.video_media_id::text
                                END,
                                'documentMediaIds', CASE
                                    WHEN jsonb_typeof(COALESCE(i.document_media_ids, '[]'::jsonb)) = 'array'
                                         AND jsonb_array_length(COALESCE(i.document_media_ids, '[]'::jsonb)) > 0
                                        THEN i.document_media_ids
                                    WHEN UPPER(i.item_type) IN ('MATERIAL', 'PDF', 'DOCUMENT') AND material.media_id IS NOT NULL
                                        THEN jsonb_build_array(material.media_id::text)
                                    ELSE '[]'::jsonb
                                END,
                                'contentUrl', i.content_url,
                                'estimatedMinutes', i.estimated_minutes,
                                'position', i.position,
                                'required', i.required
                            )
                            ORDER BY i.position
                        )
                        FROM module_items i
                        LEFT JOIN course_materials material
                            ON material.course_id = c.id AND material.id::text = i.item_id
                        WHERE i.module_id = m.id
                    ), '[]'::jsonb)
                )
                ORDER BY m.position
            )
            FROM course_modules m
            WHERE m.course_id = c.id AND m.status = 'PUBLISHED'
        ), '[]'::jsonb) AS snapshot
    FROM courses c
    WHERE c.status = 'PUBLISHED'
)
INSERT INTO course_versions (id, course_id, version_no, state, snapshot, created_by, note, published_at)
SELECT
    (substr(md5(course_id::text || ':published:' || version_no::text), 1, 8) || '-' ||
     substr(md5(course_id::text || ':published:' || version_no::text), 9, 4) || '-' ||
     substr(md5(course_id::text || ':published:' || version_no::text), 13, 4) || '-' ||
     substr(md5(course_id::text || ':published:' || version_no::text), 17, 4) || '-' ||
     substr(md5(course_id::text || ':published:' || version_no::text), 21, 12))::uuid,
    course_id,
    version_no,
    'PUBLISHED',
    snapshot,
    created_by,
    'Backfilled demo published curriculum snapshot',
    NOW()
FROM published_course_snapshots
WHERE snapshot <> '[]'::jsonb
ON CONFLICT (course_id, version_no) DO UPDATE SET
    state = EXCLUDED.state,
    snapshot = EXCLUDED.snapshot,
    note = EXCLUDED.note,
    published_at = COALESCE(course_versions.published_at, EXCLUDED.published_at);

INSERT INTO learner_module_progress (id, course_id, module_id, student_id, status, completed_at, updated_at)
VALUES
    ('34000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000001001', '4', 'COMPLETED', NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    ('34000000-0000-0000-0000-000000000102', '30000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000001002', '4', 'IN_PROGRESS', NULL, NOW() - INTERVAL '1 day'),
    ('34000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000002', '31000000-0000-0000-0000-000000000201', '4', 'IN_PROGRESS', NULL, NOW() - INTERVAL '2 days')
ON CONFLICT (module_id, student_id) DO UPDATE SET
    status = EXCLUDED.status,
    completed_at = EXCLUDED.completed_at,
    updated_at = EXCLUDED.updated_at;

\connect cf_media

INSERT INTO media_assets (id, owner_id, file_name, content_type, storage_key, size_bytes)
VALUES
    ('91000000-0000-0000-0000-000000000101', '2', 'se401-cover.svg', 'image/svg+xml', 'demo/covers/se401-cover.svg', 1800),
    ('91000000-0000-0000-0000-000000000102', '2', 'ai210-cover.svg', 'image/svg+xml', 'demo/covers/ai210-cover.svg', 1800),
    ('91000000-0000-0000-0000-000000000103', '2', 'de320-cover.svg', 'image/svg+xml', 'demo/covers/de320-cover.svg', 1800),
    ('91000000-0000-0000-0000-000000000104', '2', 'lx120-cover.svg', 'image/svg+xml', 'demo/covers/lx120-cover.svg', 1800),
    ('91000000-0000-0000-0000-000000000201', '2', 'se401-intro.mp4', 'video/mp4', 'demo/videos/se401-intro.mp4', 788493),
    ('91000000-0000-0000-0000-000000000202', '2', 'ai210-intro.mp4', 'video/mp4', 'demo/videos/ai210-intro.mp4', 788493),
    ('91000000-0000-0000-0000-000000000203', '2', 'de320-intro.mp4', 'video/mp4', 'demo/videos/de320-intro.mp4', 788493),
    ('91000000-0000-0000-0000-000000000204', '2', 'lx120-intro.mp4', 'video/mp4', 'demo/videos/lx120-intro.mp4', 788493),
    ('91000000-0000-0000-0000-000000000301', '2', 'se401-architecture-workbook.pdf', 'application/pdf', 'demo/docs/se401-architecture-workbook.pdf', 2048)
ON CONFLICT (id) DO UPDATE SET
    owner_id = EXCLUDED.owner_id,
    file_name = EXCLUDED.file_name,
    content_type = EXCLUDED.content_type,
    storage_key = EXCLUDED.storage_key,
    size_bytes = EXCLUDED.size_bytes;

INSERT INTO video_assets (id, media_asset_id, course_id, title, source_storage_key, duration_seconds, status, updated_at)
VALUES
    ('92000000-0000-0000-0000-000000000101', '91000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000001', 'Welcome: Service boundaries in practice', 'demo/videos/se401-intro.mp4', 596, 'READY', NOW()),
    ('92000000-0000-0000-0000-000000000102', '91000000-0000-0000-0000-000000000202', '30000000-0000-0000-0000-000000000002', 'Welcome: AI feature discovery', 'demo/videos/ai210-intro.mp4', 542, 'READY', NOW()),
    ('92000000-0000-0000-0000-000000000103', '91000000-0000-0000-0000-000000000203', '30000000-0000-0000-0000-000000000003', 'Welcome: Streaming pipeline walkthrough', 'demo/videos/de320-intro.mp4', 624, 'READY', NOW()),
    ('92000000-0000-0000-0000-000000000104', '91000000-0000-0000-0000-000000000204', '30000000-0000-0000-0000-000000000004', 'Welcome: Designing for online learners', 'demo/videos/lx120-intro.mp4', 511, 'READY', NOW())
ON CONFLICT (id) DO UPDATE SET
    media_asset_id = EXCLUDED.media_asset_id,
    course_id = EXCLUDED.course_id,
    title = EXCLUDED.title,
    source_storage_key = EXCLUDED.source_storage_key,
    duration_seconds = EXCLUDED.duration_seconds,
    status = EXCLUDED.status,
    updated_at = NOW();

INSERT INTO video_progress (id, video_id, user_id, position_seconds, duration_seconds, playback_rate, completed, updated_at)
VALUES
    ('93000000-0000-0000-0000-000000000101', '92000000-0000-0000-0000-000000000101', '4', 185, 596, 1.0, FALSE, NOW() - INTERVAL '2 days'),
    ('93000000-0000-0000-0000-000000000102', '92000000-0000-0000-0000-000000000102', '4', 74, 542, 1.0, FALSE, NOW() - INTERVAL '1 day')
ON CONFLICT (video_id, user_id) DO UPDATE SET
    position_seconds = EXCLUDED.position_seconds,
    duration_seconds = EXCLUDED.duration_seconds,
    playback_rate = EXCLUDED.playback_rate,
    completed = EXCLUDED.completed,
    updated_at = EXCLUDED.updated_at;

\connect cf_enrollment

INSERT INTO course_capacity (course_id, capacity, updated_at)
VALUES
    ('30000000-0000-0000-0000-000000000001', 40, NOW()),
    ('30000000-0000-0000-0000-000000000002', 35, NOW()),
    ('30000000-0000-0000-0000-000000000003', 30, NOW()),
    ('30000000-0000-0000-0000-000000000004', 45, NOW())
ON CONFLICT (course_id) DO UPDATE SET
    capacity = EXCLUDED.capacity,
    updated_at = NOW();

INSERT INTO enrollments (id, student_id, course_id, status, enrolled_at, section_id)
VALUES
    ('40000000-0000-0000-0000-000000000001', '4', '30000000-0000-0000-0000-000000000001', 'ACTIVE', NOW() - INTERVAL '14 days', '21000000-0000-0000-0000-000000000001'),
    ('40000000-0000-0000-0000-000000000002', '4', '30000000-0000-0000-0000-000000000002', 'ACTIVE', NOW() - INTERVAL '8 days', '21000000-0000-0000-0000-000000000002'),
    ('40000000-0000-0000-0000-000000000003', '5', '30000000-0000-0000-0000-000000000001', 'ACTIVE', NOW() - INTERVAL '11 days', '21000000-0000-0000-0000-000000000001'),
    ('40000000-0000-0000-0000-000000000004', '5', '30000000-0000-0000-0000-000000000004', 'ACTIVE', NOW() - INTERVAL '5 days', '21000000-0000-0000-0000-000000000004')
ON CONFLICT (student_id, course_id) DO UPDATE SET
    status = EXCLUDED.status,
    section_id = EXCLUDED.section_id;

\connect cf_assignment

INSERT INTO assignments (
    id, course_id, title, assignment_type, instructions, available_at, due_at, lock_at,
    max_score, status, submission_types, max_attempts, allow_resubmission,
    late_penalty_percent, late_penalty_interval, late_penalty_max_percent, rubric_id
)
VALUES
    ('50000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Outbox Relay Design Review', 'CODE_PROJECT', 'Implement a relay checkpoint strategy and document replay behavior for failed Kafka publishes.', NOW() - INTERVAL '10 days', NOW() + INTERVAL '9 days', NOW() + INTERVAL '12 days', 100, 'PUBLISHED', 'TEXT,URL,FILE', 2, TRUE, 5, 'DAY', 30, '51000000-0000-0000-0000-000000000001'),
    ('50000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', 'AI Evaluation Plan', 'CASE_STUDY', 'Define success metrics, red-team cases, offline eval set and launch guardrails for an AI assistant feature.', NOW() - INTERVAL '5 days', NOW() + INTERVAL '12 days', NOW() + INTERVAL '15 days', 100, 'PUBLISHED', 'TEXT,URL', 1, FALSE, 0, 'DAY', 0, '51000000-0000-0000-0000-000000000002'),
    ('50000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', 'Pipeline Reliability Runbook', 'LAB_REPORT', 'Write a runbook for backfill, bad schema rollout and late-arriving data incidents.', NOW() - INTERVAL '3 days', NOW() + INTERVAL '14 days', NOW() + INTERVAL '18 days', 100, 'PUBLISHED', 'TEXT,FILE', 1, FALSE, 3, 'DAY', 20, '51000000-0000-0000-0000-000000000003'),
    ('50000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000004', 'Lesson Storyboard Studio', 'PORTFOLIO', 'Create a lesson storyboard with outcomes, segment timing, assessment checks and accessibility notes.', NOW() - INTERVAL '2 days', NOW() + INTERVAL '10 days', NOW() + INTERVAL '14 days', 100, 'PUBLISHED', 'TEXT,URL', 2, TRUE, 0, 'DAY', 0, '51000000-0000-0000-0000-000000000004')
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    assignment_type = EXCLUDED.assignment_type,
    instructions = EXCLUDED.instructions,
    available_at = EXCLUDED.available_at,
    due_at = EXCLUDED.due_at,
    lock_at = EXCLUDED.lock_at,
    max_score = EXCLUDED.max_score,
    status = EXCLUDED.status,
    submission_types = EXCLUDED.submission_types,
    max_attempts = EXCLUDED.max_attempts,
    allow_resubmission = EXCLUDED.allow_resubmission,
    late_penalty_percent = EXCLUDED.late_penalty_percent,
    late_penalty_interval = EXCLUDED.late_penalty_interval,
    late_penalty_max_percent = EXCLUDED.late_penalty_max_percent,
    rubric_id = EXCLUDED.rubric_id;

INSERT INTO assignment_rubrics (id, assignment_id, title, max_score)
VALUES
    ('51000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 'Production readiness rubric', 100),
    ('51000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000002', 'AI evaluation rubric', 100),
    ('51000000-0000-0000-0000-000000000003', '50000000-0000-0000-0000-000000000003', 'Data runbook rubric', 100),
    ('51000000-0000-0000-0000-000000000004', '50000000-0000-0000-0000-000000000004', 'Storyboard rubric', 100)
ON CONFLICT (assignment_id) DO UPDATE SET
    title = EXCLUDED.title,
    max_score = EXCLUDED.max_score;

INSERT INTO assignment_rubric_criteria (id, rubric_id, name, description, max_points, position)
VALUES
    ('52000000-0000-0000-0000-000000000001', '51000000-0000-0000-0000-000000000001', 'Correctness and reliability', 'Handles idempotency, retries and failure recovery clearly.', 40, 1),
    ('52000000-0000-0000-0000-000000000002', '51000000-0000-0000-0000-000000000001', 'Operational clarity', 'Includes metrics, logging and rollback notes.', 35, 2),
    ('52000000-0000-0000-0000-000000000003', '51000000-0000-0000-0000-000000000001', 'Code quality', 'Small, testable changes with clear boundaries.', 25, 3),
    ('52000000-0000-0000-0000-000000000004', '51000000-0000-0000-0000-000000000002', 'Evaluation design', 'Defines measurable quality, safety and latency criteria.', 50, 1),
    ('52000000-0000-0000-0000-000000000005', '51000000-0000-0000-0000-000000000002', 'Launch risk controls', 'Documents guardrails, monitoring and rollback triggers.', 50, 2),
    ('52000000-0000-0000-0000-000000000006', '51000000-0000-0000-0000-000000000004', 'Learning alignment', 'Activities and assessments map to learner outcomes.', 50, 1),
    ('52000000-0000-0000-0000-000000000007', '51000000-0000-0000-0000-000000000004', 'Accessibility and feedback', 'Storyboard includes captions, inclusive language and feedback points.', 50, 2)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    max_points = EXCLUDED.max_points,
    position = EXCLUDED.position;

INSERT INTO submissions (
    id, assignment_id, student_id, attempt_no, submitted_at, status, submission_text,
    raw_score, final_score, grader_id, graded_at, feedback
)
VALUES
    ('53000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', '4', 1, NOW() - INTERVAL '3 days', 'GRADED', 'Submitted relay checkpoint design and rollout checklist.', 88, 88, '2', NOW() - INTERVAL '2 days', 'Strong reliability thinking. Add more alert thresholds.'),
    ('53000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000002', '4', 1, NOW() - INTERVAL '1 day', 'SUBMITTED', 'Draft evaluation plan for AI tutor recommendations.', NULL, NULL, NULL, NULL, NULL)
ON CONFLICT (assignment_id, student_id, attempt_no) DO UPDATE SET
    submitted_at = EXCLUDED.submitted_at,
    status = EXCLUDED.status,
    submission_text = EXCLUDED.submission_text,
    raw_score = EXCLUDED.raw_score,
    final_score = EXCLUDED.final_score,
    grader_id = EXCLUDED.grader_id,
    graded_at = EXCLUDED.graded_at,
    feedback = EXCLUDED.feedback;

\connect cf_quiz

INSERT INTO question_banks (id, course_id, title, created_by)
VALUES
    ('b1000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Microservice foundations', '2'),
    ('b1000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', 'AI product launch readiness', '2'),
    ('b1000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', 'Data platform reliability', '2')
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title;

INSERT INTO questions (id, bank_id, type, stem, difficulty, points, correct_answer, feedback)
VALUES
    ('b2000000-0000-0000-0000-000000000101', 'b1000000-0000-0000-0000-000000000002', 'MULTIPLE_CHOICE', 'Which artifact should be defined before shipping an AI recommendation feature?', 'EASY', 10, NULL, 'Evaluation criteria should be explicit before launch.'),
    ('b2000000-0000-0000-0000-000000000102', 'b1000000-0000-0000-0000-000000000002', 'TRUE_FALSE', 'Latency, quality and safety metrics should be tracked separately.', 'EASY', 10, NULL, 'Separate signals make launch decisions easier.'),
    ('b2000000-0000-0000-0000-000000000201', 'b1000000-0000-0000-0000-000000000003', 'MULTIPLE_CHOICE', 'What makes a data pipeline easier to recover after a bad deploy?', 'MEDIUM', 10, NULL, 'Replayability and idempotency are key recovery properties.')
ON CONFLICT (id) DO UPDATE SET
    stem = EXCLUDED.stem,
    difficulty = EXCLUDED.difficulty,
    points = EXCLUDED.points,
    feedback = EXCLUDED.feedback;

INSERT INTO question_options (id, question_id, label, content, correct, feedback)
VALUES
    ('b2100000-0000-0000-0000-000000000101', 'b2000000-0000-0000-0000-000000000101', 'A', 'A color palette for the landing page', FALSE, NULL),
    ('b2100000-0000-0000-0000-000000000102', 'b2000000-0000-0000-0000-000000000101', 'B', 'An offline evaluation set and launch threshold', TRUE, NULL),
    ('b2100000-0000-0000-0000-000000000103', 'b2000000-0000-0000-0000-000000000101', 'C', 'Only a larger prompt', FALSE, NULL),
    ('b2100000-0000-0000-0000-000000000104', 'b2000000-0000-0000-0000-000000000102', 'TRUE', 'True', TRUE, NULL),
    ('b2100000-0000-0000-0000-000000000105', 'b2000000-0000-0000-0000-000000000102', 'FALSE', 'False', FALSE, NULL),
    ('b2100000-0000-0000-0000-000000000201', 'b2000000-0000-0000-0000-000000000201', 'A', 'Manual SQL edits in every downstream database', FALSE, NULL),
    ('b2100000-0000-0000-0000-000000000202', 'b2000000-0000-0000-0000-000000000201', 'B', 'Idempotent transforms plus replayable source events', TRUE, NULL),
    ('b2100000-0000-0000-0000-000000000203', 'b2000000-0000-0000-0000-000000000201', 'C', 'Disabling monitoring during the deploy', FALSE, NULL)
ON CONFLICT (id) DO UPDATE SET
    content = EXCLUDED.content,
    correct = EXCLUDED.correct,
    feedback = EXCLUDED.feedback;

INSERT INTO quizzes (
    id, course_id, title, duration_minutes, attempts_allowed, randomize_questions,
    randomize_options, scoring_method, time_limit_enforced, show_correct_answers, status
)
VALUES
    ('b3000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Microservice Boundaries Quiz', 20, 2, TRUE, TRUE, 'HIGHEST', TRUE, TRUE, 'PUBLISHED'),
    ('b3000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', 'AI Launch Readiness Quiz', 15, 2, TRUE, TRUE, 'HIGHEST', TRUE, TRUE, 'PUBLISHED'),
    ('b3000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', 'Pipeline Reliability Quiz', 15, 2, TRUE, TRUE, 'HIGHEST', TRUE, TRUE, 'PUBLISHED')
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    duration_minutes = EXCLUDED.duration_minutes,
    attempts_allowed = EXCLUDED.attempts_allowed,
    randomize_questions = EXCLUDED.randomize_questions,
    randomize_options = EXCLUDED.randomize_options,
    scoring_method = EXCLUDED.scoring_method,
    time_limit_enforced = EXCLUDED.time_limit_enforced,
    show_correct_answers = EXCLUDED.show_correct_answers,
    status = EXCLUDED.status;

INSERT INTO quiz_questions (id, quiz_id, question_id, points, position)
VALUES
    ('b4000000-0000-0000-0000-000000000101', 'b3000000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000101', 10, 1),
    ('b4000000-0000-0000-0000-000000000102', 'b3000000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000102', 10, 2),
    ('b4000000-0000-0000-0000-000000000201', 'b3000000-0000-0000-0000-000000000003', 'b2000000-0000-0000-0000-000000000201', 10, 1)
ON CONFLICT (quiz_id, question_id) DO UPDATE SET
    points = EXCLUDED.points,
    position = EXCLUDED.position;

\connect cf_gradebook

INSERT INTO grade_categories (id, course_id, name, weight_percent, position, aggregation_method, drop_lowest)
VALUES
    ('a1000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000000002', 'Assignments', 50, 1, 'WEIGHTED_MEAN', 0),
    ('a1000000-0000-0000-0000-000000000102', '30000000-0000-0000-0000-000000000002', 'Quizzes', 30, 2, 'WEIGHTED_MEAN', 0),
    ('a1000000-0000-0000-0000-000000000103', '30000000-0000-0000-0000-000000000002', 'Studio Work', 20, 3, 'MEAN', 0),
    ('a1000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000004', 'Portfolio', 70, 1, 'WEIGHTED_MEAN', 0),
    ('a1000000-0000-0000-0000-000000000202', '30000000-0000-0000-0000-000000000004', 'Participation', 30, 2, 'MEAN', 0)
ON CONFLICT (course_id, name) DO UPDATE SET
    weight_percent = EXCLUDED.weight_percent,
    position = EXCLUDED.position,
    aggregation_method = EXCLUDED.aggregation_method,
    drop_lowest = EXCLUDED.drop_lowest;

INSERT INTO grade_items (id, course_id, category_id, source_type, source_id, title, max_score, weight_percent, late_penalty_percent)
VALUES
    ('a2000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000101', 'ASSIGNMENT', '50000000-0000-0000-0000-000000000002', 'AI Evaluation Plan', 100, 100, 0),
    ('a2000000-0000-0000-0000-000000000102', '30000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000102', 'QUIZ', 'b3000000-0000-0000-0000-000000000002', 'AI Launch Readiness Quiz', 20, 100, 0),
    ('a2000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000004', 'a1000000-0000-0000-0000-000000000201', 'ASSIGNMENT', '50000000-0000-0000-0000-000000000004', 'Lesson Storyboard Studio', 100, 100, 0)
ON CONFLICT (source_type, source_id) DO UPDATE SET
    title = EXCLUDED.title,
    max_score = EXCLUDED.max_score,
    weight_percent = EXCLUDED.weight_percent,
    late_penalty_percent = EXCLUDED.late_penalty_percent;

INSERT INTO grade_entries (id, grade_item_id, student_id, raw_score, adjusted_score, status, letter)
VALUES
    ('a3000000-0000-0000-0000-000000000101', 'a2000000-0000-0000-0000-000000000101', '4', 92, 92, 'PUBLISHED', 'A'),
    ('a3000000-0000-0000-0000-000000000102', 'a2000000-0000-0000-0000-000000000102', '4', 17, 17, 'PUBLISHED', 'A-'),
    ('a3000000-0000-0000-0000-000000000201', 'a2000000-0000-0000-0000-000000000201', '5', 86, 86, 'PUBLISHED', 'B+')
ON CONFLICT (grade_item_id, student_id) DO UPDATE SET
    raw_score = EXCLUDED.raw_score,
    adjusted_score = EXCLUDED.adjusted_score,
    status = EXCLUDED.status,
    letter = EXCLUDED.letter,
    graded_at = NOW();

INSERT INTO grading_schemes (id, course_id, name, is_default)
VALUES
    ('a6000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Default percentage scale', TRUE),
    ('a6000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', 'Default percentage scale', TRUE),
    ('a6000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000004', 'Default percentage scale', TRUE)
ON CONFLICT (course_id, name) DO UPDATE SET
    is_default = EXCLUDED.is_default;

INSERT INTO final_grades (id, course_id, student_id, final_score, letter, passed, status, finalized_by)
VALUES
    ('a7000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '4', 88, 'B+', TRUE, 'FINALIZED', '2'),
    ('a7000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', '4', 91, 'A-', TRUE, 'FINALIZED', '2')
ON CONFLICT (course_id, student_id) DO UPDATE SET
    final_score = EXCLUDED.final_score,
    letter = EXCLUDED.letter,
    passed = EXCLUDED.passed,
    status = EXCLUDED.status,
    finalized_by = EXCLUDED.finalized_by,
    finalized_at = NOW();

\connect cf_analytics

INSERT INTO course_metrics (course_id, enrolled_count, submitted_count, average_score, discussion_count, updated_at)
VALUES
    ('30000000-0000-0000-0000-000000000001', 2, 1, 88.00, 4, NOW()),
    ('30000000-0000-0000-0000-000000000002', 1, 1, 91.00, 3, NOW()),
    ('30000000-0000-0000-0000-000000000003', 0, 0, NULL, 1, NOW()),
    ('30000000-0000-0000-0000-000000000004', 1, 1, 86.00, 2, NOW())
ON CONFLICT (course_id) DO UPDATE SET
    enrolled_count = EXCLUDED.enrolled_count,
    submitted_count = EXCLUDED.submitted_count,
    average_score = EXCLUDED.average_score,
    discussion_count = EXCLUDED.discussion_count,
    updated_at = NOW();

INSERT INTO course_completion_metrics (course_id, enrolled_count, completed_count, completion_rate, avg_days_to_complete, updated_at)
VALUES
    ('30000000-0000-0000-0000-000000000001', 2, 1, 50.00, 18.5, NOW()),
    ('30000000-0000-0000-0000-000000000002', 1, 0, 35.00, NULL, NOW()),
    ('30000000-0000-0000-0000-000000000003', 0, 0, 0.00, NULL, NOW()),
    ('30000000-0000-0000-0000-000000000004', 1, 0, 20.00, NULL, NOW())
ON CONFLICT (course_id) DO UPDATE SET
    enrolled_count = EXCLUDED.enrolled_count,
    completed_count = EXCLUDED.completed_count,
    completion_rate = EXCLUDED.completion_rate,
    avg_days_to_complete = EXCLUDED.avg_days_to_complete,
    updated_at = NOW();

INSERT INTO student_time_spent (id, student_id, course_id, minutes_spent, last_activity_at)
VALUES
    ('c1000000-0000-0000-0000-000000000001', '4', '30000000-0000-0000-0000-000000000001', 420, NOW() - INTERVAL '1 day'),
    ('c1000000-0000-0000-0000-000000000002', '4', '30000000-0000-0000-0000-000000000002', 185, NOW() - INTERVAL '6 hours'),
    ('c1000000-0000-0000-0000-000000000003', '5', '30000000-0000-0000-0000-000000000004', 95, NOW() - INTERVAL '10 hours')
ON CONFLICT (student_id, course_id) DO UPDATE SET
    minutes_spent = EXCLUDED.minutes_spent,
    last_activity_at = EXCLUDED.last_activity_at,
    updated_at = NOW();

INSERT INTO course_recommendations (id, student_id, course_id, score, reason)
VALUES
    ('c2000000-0000-0000-0000-000000000001', '4', '30000000-0000-0000-0000-000000000003', 0.931, 'Recommended after Production Microservices'),
    ('c2000000-0000-0000-0000-000000000002', '4', '30000000-0000-0000-0000-000000000004', 0.812, 'Improve course design and assessment craft'),
    ('c2000000-0000-0000-0000-000000000003', '5', '30000000-0000-0000-0000-000000000002', 0.884, 'Strong fit for product analytics learners')
ON CONFLICT (student_id, course_id) DO UPDATE SET
    score = EXCLUDED.score,
    reason = EXCLUDED.reason,
    generated_at = NOW();

INSERT INTO related_courses (id, course_id, related_course_id, score)
VALUES
    ('c3000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000003', 0.920),
    ('c3000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000002', 0.880),
    ('c3000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000004', 0.790),
    ('c3000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000001', 0.910)
ON CONFLICT (course_id, related_course_id) DO UPDATE SET
    score = EXCLUDED.score;

\connect cf_review

INSERT INTO course_reviews (id, course_id, user_id, rating, title, body, status, helpful_count)
VALUES
    ('6f1e0a00-0000-4000-8000-000000000101', '30000000-0000-0000-0000-000000000001', '4', 5, 'Feels like real production work', 'The outbox and gateway sections connect directly to issues we hit in real LMS services.', 'PUBLISHED', 6),
    ('6f1e0a00-0000-4000-8000-000000000102', '30000000-0000-0000-0000-000000000001', '5', 4, 'Dense but useful', 'The labs are demanding, but the review checklists are excellent.', 'PUBLISHED', 3),
    ('6f1e0a00-0000-4000-8000-000000000201', '30000000-0000-0000-0000-000000000002', '4', 5, 'Practical AI product lens', 'I liked that it focuses on evals and rollout risk, not just prompts.', 'PUBLISHED', 5),
    ('6f1e0a00-0000-4000-8000-000000000401', '30000000-0000-0000-0000-000000000004', '5', 5, 'Great for course creators', 'The storyboard exercises made online lesson design much more concrete.', 'PUBLISHED', 2)
ON CONFLICT (course_id, user_id) DO UPDATE SET
    rating = EXCLUDED.rating,
    title = EXCLUDED.title,
    body = EXCLUDED.body,
    status = EXCLUDED.status,
    helpful_count = EXCLUDED.helpful_count,
    updated_at = NOW();

INSERT INTO course_rating_summary (course_id, review_count, average_rating, count_1, count_2, count_3, count_4, count_5)
VALUES
    ('30000000-0000-0000-0000-000000000001', 2, 4.50, 0, 0, 0, 1, 1),
    ('30000000-0000-0000-0000-000000000002', 1, 5.00, 0, 0, 0, 0, 1),
    ('30000000-0000-0000-0000-000000000003', 0, 0.00, 0, 0, 0, 0, 0),
    ('30000000-0000-0000-0000-000000000004', 1, 5.00, 0, 0, 0, 0, 1)
ON CONFLICT (course_id) DO UPDATE SET
    review_count = EXCLUDED.review_count,
    average_rating = EXCLUDED.average_rating,
    count_1 = EXCLUDED.count_1,
    count_2 = EXCLUDED.count_2,
    count_3 = EXCLUDED.count_3,
    count_4 = EXCLUDED.count_4,
    count_5 = EXCLUDED.count_5,
    updated_at = NOW();

\connect cf_announcement

INSERT INTO announcements (id, course_id, author_id, title, body, audience, status, publish_at, published_at)
VALUES
    ('70000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000000001', '2', 'Week 1: local cluster and API gateway', 'Please start the Docker local cluster before the first lab. We will trace one learner request through gateway, identity and course-service.', 'ENROLLED', 'PUBLISHED', NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days'),
    ('70000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000002', '2', 'Bring one AI feature idea', 'For the evaluation workshop, prepare one AI feature idea and one failure case you are worried about.', 'ENROLLED', 'PUBLISHED', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days')
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    body = EXCLUDED.body,
    audience = EXCLUDED.audience,
    status = EXCLUDED.status,
    publish_at = EXCLUDED.publish_at,
    published_at = EXCLUDED.published_at;

\connect cf_discussion

INSERT INTO discussion_threads (id, course_id, assignment_id, author_id, title, status)
VALUES
    ('80000000-0000-0000-0000-000000000101', '30000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', '4', 'Should each service validate JWT claims or trust gateway headers?', 'OPEN'),
    ('80000000-0000-0000-0000-000000000201', '30000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000002', '4', 'How large should my offline evaluation set be?', 'OPEN'),
    ('80000000-0000-0000-0000-000000000401', '30000000-0000-0000-0000-000000000004', '50000000-0000-0000-0000-000000000004', '5', 'What belongs in a good lesson storyboard?', 'OPEN')
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    status = EXCLUDED.status;

INSERT INTO discussion_comments (id, thread_id, author_id, body, accepted)
VALUES
    ('81000000-0000-0000-0000-000000000101', '80000000-0000-0000-0000-000000000101', '2', 'Gateway should authenticate and normalize headers, but each service still needs a local authorization backstop for sensitive mutations.', TRUE),
    ('81000000-0000-0000-0000-000000000201', '80000000-0000-0000-0000-000000000201', '2', 'Start with 50-100 labeled examples for narrow workflows, then expand around real failures after beta usage.', TRUE),
    ('81000000-0000-0000-0000-000000000401', '80000000-0000-0000-0000-000000000401', '2', 'Include outcome, scene goal, estimated time, media type, check-for-understanding and accessibility notes.', TRUE)
ON CONFLICT (id) DO UPDATE SET
    body = EXCLUDED.body,
    accepted = EXCLUDED.accepted;
