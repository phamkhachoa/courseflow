-- liquibase formatted sql
-- Single consolidated baseline for media-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:media-001-init
CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY,
    owner_id VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(120) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    size_bytes BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 002-video.sql
-- ============================================================
-- changeset courseflow:media-002-video
CREATE TABLE IF NOT EXISTS video_assets (
    id UUID PRIMARY KEY,
    media_asset_id UUID REFERENCES media_assets(id),
    course_id UUID,
    title VARCHAR(255) NOT NULL,
    source_storage_key VARCHAR(512) NOT NULL,
    duration_seconds INT,
    status VARCHAR(40) NOT NULL DEFAULT 'UPLOADED', -- UPLOADED, TRANSCODING, READY, FAILED
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Adaptive bitrate renditions produced by transcode (HLS/DASH)
CREATE TABLE IF NOT EXISTS video_renditions (
    id UUID PRIMARY KEY,
    video_id UUID NOT NULL REFERENCES video_assets(id),
    protocol VARCHAR(20) NOT NULL,          -- HLS, DASH
    label VARCHAR(40) NOT NULL,             -- 240p, 480p, 720p, 1080p
    width INT,
    height INT,
    bitrate_kbps INT,
    storage_key VARCHAR(512) NOT NULL,      -- key of the variant playlist / segment dir
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (video_id, protocol, label)
);

-- Subtitles / transcripts
CREATE TABLE IF NOT EXISTS video_captions (
    id UUID PRIMARY KEY,
    video_id UUID NOT NULL REFERENCES video_assets(id),
    language VARCHAR(16) NOT NULL,          -- vi, en, ...
    kind VARCHAR(20) NOT NULL DEFAULT 'SUBTITLE', -- SUBTITLE, TRANSCRIPT
    storage_key VARCHAR(512) NOT NULL,      -- .vtt / .srt object key
    auto_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (video_id, language, kind)
);

-- Per-user resume position and watch state
CREATE TABLE IF NOT EXISTS video_progress (
    id UUID PRIMARY KEY,
    video_id UUID NOT NULL REFERENCES video_assets(id),
    user_id VARCHAR(64) NOT NULL,
    position_seconds INT NOT NULL DEFAULT 0,
    duration_seconds INT,
    playback_rate NUMERIC(3,1) NOT NULL DEFAULT 1.0,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (video_id, user_id)
);

-- Async transcode jobs (picked up by a transcode worker)
CREATE TABLE IF NOT EXISTS transcode_jobs (
    id UUID PRIMARY KEY,
    video_id UUID NOT NULL REFERENCES video_assets(id),
    status VARCHAR(40) NOT NULL DEFAULT 'QUEUED', -- QUEUED, RUNNING, COMPLETED, FAILED
    requested_by VARCHAR(64) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_video_assets_course ON video_assets(course_id);
CREATE INDEX IF NOT EXISTS idx_video_progress_user ON video_progress(user_id);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(120) NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox_events (created_at, id)
    WHERE published_at IS NULL;

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:media-900-demo-data context=demo
INSERT INTO media_assets (id, owner_id, file_name, content_type, storage_key, size_bytes)
VALUES
  ('91000000-0000-0000-0000-000000000001', '2', 'architecture-overview.pdf', 'application/pdf', 'demo/architecture-overview.pdf', 1024)
ON CONFLICT (id) DO NOTHING;
