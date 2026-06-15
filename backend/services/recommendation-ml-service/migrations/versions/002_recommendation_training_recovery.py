from __future__ import annotations

from alembic import op

revision = "002_training_recovery"
down_revision = "001_recommendation_ml_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_training_runs_running_lock
            ON recommendation_training_runs(status, locked_at)
            WHERE status = 'RUNNING'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_recommendation_training_runs_running_lock")
