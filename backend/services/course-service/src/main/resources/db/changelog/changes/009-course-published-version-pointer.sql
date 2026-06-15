-- liquibase formatted sql

-- changeset courseflow:course-009-published-version-pointer
ALTER TABLE courses ADD COLUMN IF NOT EXISTS published_version_no INT;

UPDATE courses c
SET published_version_no = latest.version_no
FROM (
    SELECT DISTINCT ON (course_id) course_id, version_no
    FROM course_versions
    WHERE state = 'PUBLISHED'
      AND snapshot IS NOT NULL
    ORDER BY course_id, version_no DESC
) latest
WHERE c.id = latest.course_id
  AND c.published_version_no IS NULL;

