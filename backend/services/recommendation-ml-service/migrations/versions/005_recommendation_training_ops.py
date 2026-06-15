from __future__ import annotations

from alembic import op

revision = "005_recommendation_training_ops"
down_revision = "004_model_ops_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE recommendation_training_runs
            DROP CONSTRAINT IF EXISTS chk_recommendation_training_status
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_training_runs
            ADD CONSTRAINT chk_recommendation_training_status CHECK (
                status IN (
                    'QUEUED',
                    'RUNNING',
                    'STARTED',
                    'ACTIVE',
                    'INSUFFICIENT_DATA',
                    'QUALITY_GATE_FAILED',
                    'FAILED',
                    'CANCELLED'
                )
            )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_training_ops_audit (
            id UUID PRIMARY KEY,
            action VARCHAR(40) NOT NULL,
            training_run_id UUID NOT NULL REFERENCES recommendation_training_runs(id),
            previous_status VARCHAR(40),
            new_status VARCHAR(40) NOT NULL,
            actor_id VARCHAR(120) NOT NULL,
            reason VARCHAR(500) NOT NULL,
            evidence_json TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT chk_recommendation_training_ops_action CHECK (
                action IN ('TRAINING_CANCELLED', 'TRAINING_REQUEUED')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_training_ops_audit_created
            ON recommendation_training_ops_audit(created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_training_ops_audit_run
            ON recommendation_training_ops_audit(training_run_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS recommendation_training_ops_audit")
    op.execute(
        """
        ALTER TABLE recommendation_training_runs
            DROP CONSTRAINT IF EXISTS chk_recommendation_training_status
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_training_runs
            ADD CONSTRAINT chk_recommendation_training_status CHECK (
                status IN (
                    'QUEUED',
                    'RUNNING',
                    'STARTED',
                    'ACTIVE',
                    'INSUFFICIENT_DATA',
                    'QUALITY_GATE_FAILED',
                    'FAILED'
                )
            )
        """
    )
