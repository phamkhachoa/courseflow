-- liquibase formatted sql
-- changeset courseflow:user-management-900-demo-profiles context:demo splitStatements:false
--validCheckSum 9:11637ae9abb2394ebe1c327feca029d3

INSERT INTO user_profiles (user_id, display_name, avatar_url, bio, locale, timezone, visibility) VALUES
    (1, 'CourseFlow Admin', NULL, 'Platform operator for the CourseFlow demo tenant.', 'vi-VN', 'Asia/Ho_Chi_Minh', 'PRIVATE'),
    (2, 'Demo Instructor', NULL, 'Instructor profile used by demo authoring workflows.', 'vi-VN', 'Asia/Ho_Chi_Minh', 'ORG'),
    (4, 'Demo Learner', NULL, 'Learner profile used by demo enrollment and learning workflows.', 'vi-VN', 'Asia/Ho_Chi_Minh', 'PUBLIC'),
    (5, 'Product Analyst Learner', NULL, 'Second learner profile used by analytics and review demo data.', 'vi-VN', 'Asia/Ho_Chi_Minh', 'PUBLIC')
ON CONFLICT (user_id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    bio = EXCLUDED.bio,
    locale = EXCLUDED.locale,
    timezone = EXCLUDED.timezone,
    visibility = EXCLUDED.visibility,
    updated_at = NOW();
