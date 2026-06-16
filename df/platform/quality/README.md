# Data Quality Platform

Data quality is a release gate, not a dashboard-only concern.

## Implemented Quality Profiles

`profiles.yaml` is the metadata-as-code registry for production quality policy. Use-case
implementations reference a profile through `qualityProfile`; `enterprise-df validate` checks that
the profile exists, applies to the use case and primary output, and only requires columns that exist
in data-product contracts.

Generic `run-use-case` release evidence evaluates the profile through `P0-QUALITY-PROFILE`:

- Quarantine rows must stay within the profile threshold.
- Primary output rows must meet the minimum row threshold.
- Upstream and all declared output layers must pass when required.
- Required outputs must have content hashes when required.
- Evidence records the profile id and profile registry hash for audit correlation.

## Required Check Families

- Schema: expected columns and compatible types.
- Freshness: max lag per data product.
- Volume: row-count anomaly and empty partition detection.
- Validity: enum/domain checks and date bounds.
- Uniqueness: primary keys and idempotency keys.
- Referential integrity: known product, organization, account or person references where allowed.
- Privacy: PII tags, masking and tenant isolation checks.
