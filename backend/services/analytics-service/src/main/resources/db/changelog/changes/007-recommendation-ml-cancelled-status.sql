-- liquibase formatted sql
-- changeset courseflow:analytics-007-recommendation-ml-cancelled-status
ALTER TABLE recommendation_ml_training_jobs
    DROP CONSTRAINT IF EXISTS chk_recommendation_ml_training_job_status;

ALTER TABLE recommendation_ml_training_jobs
    ADD CONSTRAINT chk_recommendation_ml_training_job_status CHECK (
        status IN (
            'QUEUED',
            'RUNNING',
            'STARTED',
            'ACTIVE',
            'INSUFFICIENT_DATA',
            'QUALITY_GATE_FAILED',
            'FAILED',
            'CANCELLED',
            'FAILED_TO_ENQUEUE',
            'UNAVAILABLE'
        )
    );
