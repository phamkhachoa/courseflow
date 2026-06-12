-- liquibase formatted sql

-- changeset courseflow:course-002-rich-lesson-items
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS video_media_id UUID;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS document_media_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS content_url TEXT;
ALTER TABLE module_items ADD COLUMN IF NOT EXISTS estimated_minutes INT;
