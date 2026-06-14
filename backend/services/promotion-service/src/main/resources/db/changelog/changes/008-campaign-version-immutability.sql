-- liquibase formatted sql
-- Keep published campaign versions as immutable runtime/legal snapshots.

-- changeset courseflow:promotion-008-campaign-version-immutability splitStatements:false
CREATE OR REPLACE FUNCTION protect_published_incentive_campaign_version()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND OLD.version_status IN ('PUBLISHED', 'SUPERSEDED') THEN
        RAISE EXCEPTION 'Published campaign versions are immutable and cannot be deleted: campaign %, version %',
            OLD.campaign_id, OLD.version_number;
    END IF;

    IF TG_OP = 'UPDATE' AND OLD.version_status IN ('PUBLISHED', 'SUPERSEDED') THEN
        IF OLD.version_status = 'PUBLISHED'
            AND OLD.active_snapshot = TRUE
            AND NEW.active_snapshot = FALSE
            AND NEW.version_status IN ('PUBLISHED', 'SUPERSEDED')
            AND NEW.id IS NOT DISTINCT FROM OLD.id
            AND NEW.campaign_id IS NOT DISTINCT FROM OLD.campaign_id
            AND NEW.tenant_id IS NOT DISTINCT FROM OLD.tenant_id
            AND NEW.application_id IS NOT DISTINCT FROM OLD.application_id
            AND NEW.code IS NOT DISTINCT FROM OLD.code
            AND NEW.name IS NOT DISTINCT FROM OLD.name
            AND NEW.description IS NOT DISTINCT FROM OLD.description
            AND NEW.incentive_type IS NOT DISTINCT FROM OLD.incentive_type
            AND NEW.version_number IS NOT DISTINCT FROM OLD.version_number
            AND NEW.starts_at IS NOT DISTINCT FROM OLD.starts_at
            AND NEW.ends_at IS NOT DISTINCT FROM OLD.ends_at
            AND NEW.priority IS NOT DISTINCT FROM OLD.priority
            AND NEW.exclusive IS NOT DISTINCT FROM OLD.exclusive
            AND NEW.stackable IS NOT DISTINCT FROM OLD.stackable
            AND NEW.coupon_required IS NOT DISTINCT FROM OLD.coupon_required
            AND NEW.match_policy IS NOT DISTINCT FROM OLD.match_policy
            AND NEW.currency IS NOT DISTINCT FROM OLD.currency
            AND NEW.rules_json IS NOT DISTINCT FROM OLD.rules_json
            AND NEW.actions_json IS NOT DISTINCT FROM OLD.actions_json
            AND NEW.max_redemptions IS NOT DISTINCT FROM OLD.max_redemptions
            AND NEW.max_redemptions_per_profile IS NOT DISTINCT FROM OLD.max_redemptions_per_profile
            AND NEW.rollback_source_version IS NOT DISTINCT FROM OLD.rollback_source_version
            AND NEW.created_by IS NOT DISTINCT FROM OLD.created_by
            AND NEW.submitted_by IS NOT DISTINCT FROM OLD.submitted_by
            AND NEW.reviewed_by IS NOT DISTINCT FROM OLD.reviewed_by
            AND NEW.published_by IS NOT DISTINCT FROM OLD.published_by
            AND NEW.review_note IS NOT DISTINCT FROM OLD.review_note
            AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
            AND NEW.submitted_at IS NOT DISTINCT FROM OLD.submitted_at
            AND NEW.reviewed_at IS NOT DISTINCT FROM OLD.reviewed_at
            AND NEW.published_at IS NOT DISTINCT FROM OLD.published_at THEN
            RETURN NEW;
        END IF;

        RAISE EXCEPTION 'Published campaign versions are immutable and cannot be updated: campaign %, version %',
            OLD.campaign_id, OLD.version_number;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_protect_published_incentive_campaign_version
    ON incentive_campaign_versions;

CREATE TRIGGER trg_protect_published_incentive_campaign_version
BEFORE UPDATE OR DELETE ON incentive_campaign_versions
FOR EACH ROW
EXECUTE FUNCTION protect_published_incentive_campaign_version();
