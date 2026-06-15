-- liquibase formatted sql
-- changeset courseflow:analytics-008-recommendation-ml-pending-activation-status
ALTER TABLE recommendation_ml_training_jobs
    DROP CONSTRAINT IF EXISTS chk_recommendation_ml_training_job_status;

ALTER TABLE recommendation_ml_training_jobs
    ADD CONSTRAINT chk_recommendation_ml_training_job_status CHECK (
        status IN (
            'QUEUED',
            'RUNNING',
            'STARTED',
            'ACTIVE',
            'PENDING_ACTIVATION',
            'ACTIVATION_REJECTED',
            'INSUFFICIENT_DATA',
            'QUALITY_GATE_FAILED',
            'FAILED',
            'CANCELLED',
            'FAILED_TO_ENQUEUE',
            'UNAVAILABLE'
        )
    );
