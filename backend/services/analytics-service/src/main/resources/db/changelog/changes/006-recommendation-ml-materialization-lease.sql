-- liquibase formatted sql
-- changeset courseflow:analytics-006-recommendation-ml-materialization-lease
ALTER TABLE recommendation_ml_training_jobs
    ADD COLUMN IF NOT EXISTS materialization_locked_by VARCHAR(120);

ALTER TABLE recommendation_ml_training_jobs
    ADD COLUMN IF NOT EXISTS materialization_locked_at TIMESTAMPTZ;

ALTER TABLE recommendation_ml_training_jobs
    ADD COLUMN IF NOT EXISTS materialization_attempt_count INT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_recommendation_ml_training_jobs_materialization_lease
    ON recommendation_ml_training_jobs(status, materialization_locked_at, submitted_at)
    WHERE materialized_at IS NULL;
