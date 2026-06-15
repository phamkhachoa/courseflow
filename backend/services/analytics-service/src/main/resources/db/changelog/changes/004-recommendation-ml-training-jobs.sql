-- liquibase formatted sql
-- changeset courseflow:analytics-004-recommendation-ml-training-jobs
CREATE TABLE IF NOT EXISTS recommendation_ml_training_jobs (
    training_run_id UUID PRIMARY KEY,
    model_version VARCHAR(80),
    status VARCHAR(40) NOT NULL,
    since_at TIMESTAMPTZ,
    limit_per_course INT NOT NULL DEFAULT 24,
    engine VARCHAR(40) NOT NULL DEFAULT 'ML_ASYNC',
    fallback_reason VARCHAR(160),
    pair_count INT NOT NULL DEFAULT 0,
    generated_related_rows INT NOT NULL DEFAULT 0,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    materialized_at TIMESTAMPTZ,
    check_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_recommendation_ml_training_job_status CHECK (
        status IN (
            'QUEUED',
            'RUNNING',
            'STARTED',
            'ACTIVE',
            'INSUFFICIENT_DATA',
            'QUALITY_GATE_FAILED',
            'FAILED',
            'FAILED_TO_ENQUEUE',
            'UNAVAILABLE'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_recommendation_ml_training_jobs_pending
    ON recommendation_ml_training_jobs(status, last_checked_at, submitted_at)
    WHERE materialized_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_recommendation_ml_training_jobs_model
    ON recommendation_ml_training_jobs(model_version, submitted_at DESC);
