from __future__ import annotations

from alembic import op

revision = "004_model_ops_audit"
down_revision = "003_recommendation_quality_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_model_ops_audit (
            id UUID PRIMARY KEY,
            action VARCHAR(40) NOT NULL,
            model_version VARCHAR(80) NOT NULL,
            previous_active_model_version VARCHAR(80),
            actor_id VARCHAR(120) NOT NULL,
            reason VARCHAR(500) NOT NULL,
            evidence_json TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT chk_recommendation_model_ops_action CHECK (
                action IN ('TRAINING_ACTIVATED', 'MODEL_REACTIVATED')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_model_ops_audit_created
            ON recommendation_model_ops_audit(created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_model_ops_audit_model
            ON recommendation_model_ops_audit(model_version, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS recommendation_model_ops_audit")
