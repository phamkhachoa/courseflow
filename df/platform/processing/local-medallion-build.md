# Local Medallion Build Preflight

`enterprise-df build-recommendation` is the first local processing preflight that builds Silver and
Gold outputs from approved Bronze JSONL. New work should prefer the generic runner interface:
`enterprise-df pipeline-list` and `enterprise-df run-pipeline`.

It intentionally reads approved Bronze output from `enterprise-df ingest-bronze`, not raw product
events. This preserves the production boundary:

```text
raw event JSONL
  -> ingest-bronze
  -> approved Bronze + quarantine + ingestion manifest
  -> run-pipeline recommendation.from_approved_bronze.v1
  -> Silver activity + Gold recommendation interactions + ML handoff manifest
```

## Example

```bash
cd df
PYTHONPATH=src python -m enterprise_df.cli build-recommendation \
  --bronze build/recommendation-ingestion/bronze/events_recommendation_tracking.jsonl \
  --upstream-manifest build/recommendation-ingestion/manifests/events_recommendation_tracking.local-recommendation-ingest-001.json \
  --output-dir build/recommendation-medallion \
  --snapshot-id local-recsys-001
```

Generic runner equivalent:

```bash
cd df
PYTHONPATH=src python -m enterprise_df.cli pipeline-list
PYTHONPATH=src python -m enterprise_df.cli pipeline-list --use-case ml-feature-governance
PYTHONPATH=src python -m enterprise_df.cli pipeline-describe \
  --runner-id recommendation.from_approved_bronze.v1
PYTHONPATH=src python -m enterprise_df.cli run-pipeline \
  --runner-id recommendation.from_approved_bronze.v1 \
  --input build/recommendation-ingestion/bronze/events_recommendation_tracking.jsonl \
  --upstream-manifest build/recommendation-ingestion/manifests/events_recommendation_tracking.local-recommendation-ingest-001.json \
  --output-dir build/recommendation-medallion \
  --snapshot-id local-recsys-001
```

## Evidence Rules

- The output manifest records the upstream ingestion manifest path and hash.
- Source offset ranges are copied from the upstream ingestion manifest.
- `upstream_quality_passed=false` blocks publishability even if Silver/Gold row checks pass.
- Gold output remains a deterministic snapshot keyed by `dataset_snapshot_id`.
- Registered runners must declare product, domain, use cases, input kind and output data products.
