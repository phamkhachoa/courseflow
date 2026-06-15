-- liquibase formatted sql
-- changeset courseflow:loyalty-011-approval-zero-delta-fulfillment

ALTER TABLE loyalty_adjustment_approvals
    DROP CONSTRAINT IF EXISTS chk_loyalty_adjustment_approval_delta;

ALTER TABLE loyalty_adjustment_approvals
    ADD CONSTRAINT chk_loyalty_adjustment_approval_delta CHECK (
        points_delta <> 0
        OR COALESCE(metadata_json ->> 'operationType', '') = 'REWARD_FULFILLMENT_OVERRIDE'
    );
