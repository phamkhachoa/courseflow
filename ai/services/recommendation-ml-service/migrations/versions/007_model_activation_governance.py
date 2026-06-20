from __future__ import annotations

from alembic import op

revision = "007_model_activation_governance"
down_revision = "006_model_activation_approval"
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
                    'PENDING_ACTIVATION',
                    'ACTIVATION_REJECTED',
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
        ALTER TABLE recommendation_model_versions
            DROP CONSTRAINT IF EXISTS chk_recommendation_model_status
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_model_versions
            ADD CONSTRAINT chk_recommendation_model_status CHECK (
                status IN ('CANDIDATE', 'ACTIVE', 'SUPERSEDED', 'REJECTED')
            )
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_model_ops_audit
            DROP CONSTRAINT IF EXISTS chk_recommendation_model_ops_action
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_model_ops_audit
            ADD CONSTRAINT chk_recommendation_model_ops_action CHECK (
                action IN (
                    'TRAINING_CANDIDATE_REGISTERED',
                    'TRAINING_ACTIVATED',
                    'MODEL_ACTIVATION_REJECTED',
                    'MODEL_REACTIVATED'
                )
            )
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY model_version
                       ORDER BY created_at DESC, id DESC
                   ) AS duplicate_rank
              FROM recommendation_model_activation_approvals
             WHERE status = 'PENDING'
        )
        UPDATE recommendation_model_activation_approvals approval
           SET status = 'REJECTED',
               reviewed_by = 'system:migration-007',
               review_reason = 'Superseded by a newer pending activation request '
                   || 'during migration 007',
               reviewed_at = NOW()
          FROM ranked
         WHERE approval.id = ranked.id
           AND ranked.duplicate_rank > 1
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_recommendation_model_activation_one_pending_per_model
            ON recommendation_model_activation_approvals(model_version)
            WHERE status = 'PENDING'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ux_recommendation_model_activation_one_pending_per_model
        """
    )
    op.execute(
        """
        UPDATE recommendation_model_ops_audit
           SET action = 'TRAINING_ACTIVATED',
               reason = CONCAT('[downgraded from candidate audit] ', reason)
         WHERE action = 'TRAINING_CANDIDATE_REGISTERED'
        """
    )
    op.execute(
        """
        UPDATE recommendation_model_ops_audit
           SET action = 'MODEL_REACTIVATED',
               reason = CONCAT('[downgraded from activation rejection audit] ', reason)
         WHERE action = 'MODEL_ACTIVATION_REJECTED'
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_model_ops_audit
            DROP CONSTRAINT IF EXISTS chk_recommendation_model_ops_action
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_model_ops_audit
            ADD CONSTRAINT chk_recommendation_model_ops_action CHECK (
                action IN ('TRAINING_ACTIVATED', 'MODEL_REACTIVATED')
            )
        """
    )
    op.execute(
        """
        UPDATE recommendation_model_versions
           SET status = 'SUPERSEDED',
               superseded_at = COALESCE(superseded_at, trained_at)
         WHERE status = 'CANDIDATE'
        """
    )
    op.execute(
        """
        UPDATE recommendation_model_versions
           SET status = 'SUPERSEDED'
         WHERE status = 'REJECTED'
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_model_versions
            DROP CONSTRAINT IF EXISTS chk_recommendation_model_status
        """
    )
    op.execute(
        """
        ALTER TABLE recommendation_model_versions
            ADD CONSTRAINT chk_recommendation_model_status CHECK (
                status IN ('ACTIVE', 'SUPERSEDED')
            )
        """
    )
    op.execute(
        """
        UPDATE recommendation_training_runs
           SET status = 'FAILED',
               error_class = 'DOWNGRADED_PENDING_ACTIVATION',
               error_message = 'PENDING_ACTIVATION cannot be represented before migration 007'
         WHERE status = 'PENDING_ACTIVATION'
        """
    )
    op.execute(
        """
        UPDATE recommendation_training_runs
           SET status = 'FAILED',
               error_class = 'DOWNGRADED_ACTIVATION_REJECTED',
               error_message = 'ACTIVATION_REJECTED cannot be represented before migration 007'
         WHERE status = 'ACTIVATION_REJECTED'
        """
    )
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
