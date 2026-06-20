# Enterprise Data Catalog

`catalog/` is the metadata-as-code home for data discovery, ownership, glossary and lineage
registration. The runtime catalog may be DataHub, OpenMetadata, Atlan or Collibra, but this folder
keeps the source-controlled intent.

## Required Catalog Metadata

Every published data product must register:

- Product code and enterprise domain.
- Product owner, domain owner, technical owner and data steward.
- Business definition and glossary terms.
- PII classification, data residency, retention and erasure support.
- Upstream lineage and downstream consumers.
- SLA/SLO, quality gates and publication evidence.
- Access personas and consumer contract.
- Change-control request, approval and evidence state for production-impacting changes.
- Deprecation policy and compatibility guarantees.

## Local Export

Use [catalog-bundle.md](catalog-bundle.md) for the P0 metadata bundle export. The bundle is the local
handoff format for future DataHub/OpenMetadata integration.

`enterprise-dp catalog-publish-manifest` creates the auditable publish manifest for DataHub or
OpenMetadata. Production-like publication must attach the catalog bundle hash, OpenLineage artifact,
semantic view manifest, requester and change ticket before catalog publish is considered ready.

`enterprise-dp catalog-lineage-ops-report` is the Control Tower-facing gate. It consumes the catalog
bundle, publish manifest, OpenLineage artifact and optional publish receipt, then reports whether
catalog and lineage evidence is ready for the target environment.
