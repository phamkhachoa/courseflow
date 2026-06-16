from __future__ import annotations

from alembic import op

revision = "001_recommendation_ml_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_training_runs (
            id UUID PRIMARY KEY,
            requested_model_version VARCHAR(80),
            activated_model_version VARCHAR(80),
            algorithm VARCHAR(80) NOT NULL,
            status VARCHAR(40) NOT NULL,
            request_hash VARCHAR(96) NOT NULL,
            event_count INT NOT NULL DEFAULT 0,
            principal_count INT NOT NULL DEFAULT 0,
            course_count INT NOT NULL DEFAULT 0,
            pair_count INT NOT NULL DEFAULT 0,
            quality_score NUMERIC(8,6) NOT NULL DEFAULT 0,
            min_support INT NOT NULL DEFAULT 1,
            max_related_per_course INT NOT NULL DEFAULT 24,
            error_class VARCHAR(120),
            error_message VARCHAR(500),
            requested_by VARCHAR(120),
            payload_json TEXT,
            attempt_count INT NOT NULL DEFAULT 0,
            locked_by VARCHAR(120),
            locked_at TIMESTAMPTZ,
            available_at TIMESTAMPTZ,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            CONSTRAINT chk_recommendation_training_status CHECK (
                status IN ('QUEUED', 'RUNNING', 'STARTED', 'ACTIVE', 'INSUFFICIENT_DATA', 'FAILED')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_training_runs_status
            ON recommendation_training_runs(status, started_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_training_runs_queue
            ON recommendation_training_runs(status, available_at, started_at)
            WHERE status = 'QUEUED'
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_model_versions (
            id UUID PRIMARY KEY,
            model_version VARCHAR(80) NOT NULL UNIQUE,
            training_run_id UUID NOT NULL REFERENCES recommendation_training_runs(id),
            algorithm VARCHAR(80) NOT NULL,
            status VARCHAR(40) NOT NULL,
            event_count INT NOT NULL DEFAULT 0,
            principal_count INT NOT NULL DEFAULT 0,
            course_count INT NOT NULL DEFAULT 0,
            pair_count INT NOT NULL DEFAULT 0,
            quality_score NUMERIC(8,6) NOT NULL DEFAULT 0,
            params_json TEXT,
            training_hash VARCHAR(96) NOT NULL,
            created_by VARCHAR(120),
            trained_at TIMESTAMPTZ NOT NULL,
            activated_at TIMESTAMPTZ,
            superseded_at TIMESTAMPTZ,
            CONSTRAINT chk_recommendation_model_status CHECK (
                status IN ('ACTIVE', 'SUPERSEDED')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_model_versions_active
            ON recommendation_model_versions(status, activated_at DESC)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_recommendation_model_versions_one_active
            ON recommendation_model_versions(status)
            WHERE status = 'ACTIVE'
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_related_course_scores (
            id UUID PRIMARY KEY,
            model_version VARCHAR(80) NOT NULL REFERENCES recommendation_model_versions(model_version),
            course_id UUID NOT NULL,
            related_course_id UUID NOT NULL,
            rank INT NOT NULL,
            score NUMERIC(8,6) NOT NULL,
            similarity NUMERIC(8,6) NOT NULL,
            support_count INT NOT NULL DEFAULT 0,
            reason_code VARCHAR(80) NOT NULL,
            generated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT chk_recommendation_score_not_self CHECK (course_id <> related_course_id),
            CONSTRAINT ux_recommendation_score_model_pair UNIQUE (
                model_version, course_id, related_course_id
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_scores_model_course
            ON recommendation_related_course_scores(model_version, course_id, rank, score DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS recommendation_related_course_scores")
    op.execute("DROP TABLE IF EXISTS recommendation_model_versions")
    op.execute("DROP TABLE IF EXISTS recommendation_training_runs")
