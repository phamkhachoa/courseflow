# Catalog Bundle Export

`enterprise-df catalog-export` creates a source-controlled metadata bundle that can later be pushed
to DataHub, OpenMetadata, Atlan or Collibra.

The bundle is intentionally local JSON for P0. It gives platform, domain and governance teams an
auditable artifact before a runtime catalog integration exists.

Use `enterprise-df openlineage-export` to convert a bundle plus run manifests into OpenLineage-style
runtime events for a lineage backend or async publisher.

Use `enterprise-df catalog-publish-manifest` after catalog, lineage and semantic-view artifacts are
created. It produces `catalog_publish_manifest.v1`, the release evidence that records the target
catalog system, bundle hash, lineage hash, semantic view hash and production-like publish checks.

Change-control entries are included so DataHub/OpenMetadata can expose not just datasets and lineage,
but also the approval state, risk level, target environment and evidence references behind source
onboarding, catalog publish, semantic layer and Gold release changes.

## Inputs

- Product onboarding metadata under `products/*/onboarding.yaml`.
- Enterprise domain registry at `domains/registry.yaml`.
- Enterprise use-case portfolio at `use-cases/registry.yaml`.
- Enterprise change-control registry at `governance/change-requests.yaml`.
- Topic contracts under `contracts/topics/`.
- Data product contracts under `contracts/data-products/`.
- Optional ingestion or processing manifests from local pipeline runs.

## Example

```bash
cd df
PYTHONPATH=src python -m enterprise_df.cli catalog-export \
  --root . \
  --output build/catalog/catalog-bundle.json \
  --manifest build/recommendation-ingestion/manifests/events_recommendation_tracking.local-recommendation-ingest-001.json \
  --manifest build/recommendation-medallion/manifests/recsys_interactions.local-recsys-001.json

PYTHONPATH=src python -m enterprise_df.cli catalog-publish-manifest \
  --catalog build/catalog/catalog-bundle.json \
  --openlineage-events build/lineage/openlineage-events.jsonl \
  --semantic-views build/serving/semantic-views.json \
  --output build/catalog/catalog-publish.json \
  --target-system datahub \
  --environment staging \
  --endpoint https://datahub.staging.example \
  --requested-by data-platform-release-manager \
  --change-ticket CHG-DF-1001
```

## Bundle Contents

| Section | Purpose |
|---|---|
| `products` | Product ownership, tenant model, source systems and first-slice assets. |
| `products[].governance` | Product default privacy, retention, access, release evidence, lineage and catalog controls. |
| `domains` | Enterprise domain registry and BA/PO capability map. |
| `use_cases` | Group-wide business use cases, owners, consumers, KPIs, planned/existing data products, pipeline runners and release gates. |
| `change_requests` | Maker-checker request workflow, risk level, target environment, approvals and evidence references. |
| `topics` | Topic ownership, schema compatibility, privacy and Bronze target metadata. |
| `data_products` | Bronze/Silver/Gold ownership, schema, PII, quality, serving and lineage metadata. |
| `lineage_edges` | Static contract lineage plus run-level transformation lineage. |
| `run_evidence` | Ingestion/processing manifest evidence: quality, row count, hashes and source offsets. |

## Governance Rules

- Every published Gold product must have a catalog bundle entry before activation.
- Every P0/P1 use case must declare owner, domain, consumers, data products, governance and release
  gates before implementation starts.
- Run evidence must include the upstream ingestion manifest hash when Gold is built from Bronze.
- Run manifests should declare explicit `lineage_edges`; catalog export uses those edges for
  `RUN_LAYER_TRANSFORM` instead of inferring from JSON object key order.
- Production-like catalog publish, semantic layer and Gold activation changes should have a passing
  change-control evidence report before activation.
- Catalog lineage is not a replacement for quality gates; `quality_passed=false` remains a publish
  blocker.
- The bundle is safe to store in CI artifacts. It contains hashes and metadata, not raw row payloads.
