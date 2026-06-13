-- liquibase formatted sql
-- Backfill frozen snapshots for courses that were already marked PUBLISHED before
-- learner curriculum reads were switched to snapshot-only mode.

-- changeset courseflow:course-005-backfill-published-course-snapshots
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
  'Backfilled published curriculum snapshot',
  NOW()
FROM published_course_snapshots
WHERE snapshot <> '[]'::jsonb
ON CONFLICT (course_id, version_no) DO UPDATE SET
  state = EXCLUDED.state,
  snapshot = EXCLUDED.snapshot,
  note = EXCLUDED.note,
  published_at = COALESCE(course_versions.published_at, EXCLUDED.published_at)
WHERE course_versions.snapshot IS NULL
   OR course_versions.snapshot = '[]'::jsonb;
