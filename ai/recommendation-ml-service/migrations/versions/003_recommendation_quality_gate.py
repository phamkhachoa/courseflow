from __future__ import annotations

from alembic import op

revision = "003_recommendation_quality_gate"
down_revision = "002_training_recovery"
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
                    'FAILED'
                )
            )
        """
    )


def downgrade() -> None:
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
                status IN ('QUEUED', 'RUNNING', 'STARTED', 'ACTIVE', 'INSUFFICIENT_DATA', 'FAILED')
            )
        """
    )
