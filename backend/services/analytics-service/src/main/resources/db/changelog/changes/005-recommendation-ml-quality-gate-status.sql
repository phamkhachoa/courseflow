-- liquibase formatted sql
-- changeset courseflow:analytics-005-recommendation-ml-quality-gate-status
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
            'FAILED_TO_ENQUEUE',
            'UNAVAILABLE'
        )
    );
