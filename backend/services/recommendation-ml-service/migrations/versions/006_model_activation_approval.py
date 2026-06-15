from __future__ import annotations

from alembic import op

revision = "006_model_activation_approval"
down_revision = "005_recommendation_training_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_model_activation_approvals (
            id UUID PRIMARY KEY,
            model_version VARCHAR(80) NOT NULL
                REFERENCES recommendation_model_versions(model_version),
            status VARCHAR(40) NOT NULL,
            requested_by VARCHAR(120) NOT NULL,
            request_reason VARCHAR(500) NOT NULL,
            request_evidence_json TEXT,
            reviewed_by VARCHAR(120),
            review_reason VARCHAR(500),
            review_evidence_json TEXT,
            previous_active_model_version VARCHAR(80),
            created_at TIMESTAMPTZ NOT NULL,
            reviewed_at TIMESTAMPTZ,
            executed_at TIMESTAMPTZ,
            CONSTRAINT chk_recommendation_model_activation_approval_status CHECK (
                status IN ('PENDING', 'REJECTED', 'EXECUTED')
            ),
            CONSTRAINT chk_recommendation_model_activation_checker_diff CHECK (
                reviewed_by IS NULL OR reviewed_by <> requested_by
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_model_activation_approvals_status
            ON recommendation_model_activation_approvals(status, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recommendation_model_activation_approvals_model
            ON recommendation_model_activation_approvals(model_version, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS recommendation_model_activation_approvals")
