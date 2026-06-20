# Catalog and Lineage Operations Gate

`catalog_lineage_ops_report.v1` is the P0 operations gate for enterprise catalog and lineage
publication. It sits above the local catalog bundle, OpenLineage export and catalog publish manifest
so Control Tower can decide whether metadata is ready for production signoff.

## Decision

`enterprise-dp catalog-lineage-ops-report` reads:

- A catalog bundle from `enterprise-dp catalog-export`, or generates one from the repository root.
- An optional `catalog_publish_manifest.v1`.
- An optional OpenLineage JSONL artifact.
- An optional `catalog_publish_receipt.v1` emitted by a DataHub/OpenMetadata publish job.

Local environments may pass as a preflight without publish artifacts. Staging and production fail
closed unless catalog publish evidence, valid OpenLineage events and a runtime publish receipt are
attached.

Control Tower consumes the report through `--catalog-lineage-ops-report` and blocks production
signoff when the artifact is from the wrong environment, has the wrong readiness state, fails its
checks, or references a catalog hash different from the Control Tower catalog input.
The production review pack uses the same report as a strict release gate: only a staging/prod
`runtime_attested` report with `readiness_state=production_like_ready` can remove the
`catalog-lineage-control-plane` blocker. A local preflight report may pass, but remains partner
review evidence and never closes the production capability gap.

## Evidence Contract

The report verifies:

- Catalog bundle hash and summary are present.
- Catalog publish manifest is `catalog_publish_manifest.v1`, passing and for the target environment.
- Catalog hash in the publish manifest matches the Control Tower catalog bundle.
- Production-like publishes declare endpoint, requester and change ticket.
- OpenLineage JSONL parses and validates as OpenLineage-style events.
- Production-like OpenLineage namespace and producer are not local placeholders.
- Production-like publishes attach `catalog_publish_receipt.v1` with matching environment, target,
  catalog bundle hash, publish manifest hash and OpenLineage hash.
- Product rows keep owner, data steward, static lineage, runtime event count, last runtime run and
  catalog publish status visible for Control Tower Gold materialization.

`catalog_publish_receipt.v1` is the boundary for future live DataHub/OpenMetadata integration. In
this repository it is only consumed as evidence; no remote catalog is contacted by local tooling.

## CLI

```bash
enterprise-dp catalog-lineage-ops-report \
  --root . \
  --environment prod \
  --catalog build/catalog/catalog-bundle.json \
  --catalog-publish-manifest build/catalog/catalog-publish.json \
  --openlineage-events build/lineage/openlineage-events.jsonl \
  --publish-receipt build/catalog/catalog-publish-receipt-prod.json \
  --output build/evidence/catalog-lineage-ops-prod.json
```

The command exits non-zero when global catalog/lineage evidence fails or a data product has missing
ownership, missing static lineage or missing runtime lineage in production-like environments.

## Current State

This repository has the report contract, CLI, Control Tower gate, production review pack gate and
tests. The capability remains at L1 for local runs because catalog publication is still
artifact-backed; L2/L3 require a staging or production DataHub/OpenMetadata/OpenLineage runtime that
emits the publish receipt and collector evidence automatically.
