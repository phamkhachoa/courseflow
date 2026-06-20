# Production Data Platform Environment

Production requires least-privilege service identities, encrypted storage, cataloged assets, quality
gates, retention policy, access audit and release evidence before Gold data products are activated.
`manifest.yaml` is the production runtime contract for required P0 services and signoff evidence.

## P0 Release Gate Checklist

Before any production deploy that changes P0 ingestion, transformations, contracts, quality checks or
Gold publication, the release owner must attach the evidence pack defined in
`dp/platform/observability/production-slo-release-gates.md`.

Required pass conditions:

- `P0-INGESTION-LAG`: each registered P0 source topic or CDC source lands in Bronze inside its
  declared SLO.
- `P0-FRESHNESS`: Bronze, Silver and Gold products meet the freshness SLO declared by their data
  product contract and release profile.
- `P0-QUALITY`: all required checks pass; privacy, tenant isolation and sensitive payload checks have
  zero failures.
- `P0-CONTRACT-COMPATIBILITY`: local contract validation and external schema compatibility both pass.
- `P0-GOLD-EVIDENCE`: every activated Gold snapshot has durable publish evidence before consumers
  read it.
- `P0-RUNTIME-IAC`: production runtime readiness report passes with IaC apply evidence, external
  secrets, service identity, private network, backup and DR evidence attached.

## Production Signoff

- Staging gate evidence must be captured first using production-like topology and masked data.
- Production deploy approval must include the current production gate status, not only CI status.
- Gold activation must be a separate, auditable step tied to `gold_dataset_snapshot_id`.
- If any gate is red, freeze the impacted downstream publish and follow
  `dp/ops-runbooks/data-platform-p0-gates.md`.
