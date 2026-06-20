# Recommendation Local Pipeline

This skeleton implements the first local medallion path for recommendation tracking. The production
direction is to build Silver and Gold from approved Bronze output, not directly from raw product
events.

```text
recommendation tracking JSONL
  -> contract-checked approved Bronze + quarantine
  -> silver.learner_activity
  -> gold.recsys_interactions
  -> snapshot manifest
```

## Local Entry Point

Preferred local CLI flow:

```bash
cd dp
PYTHONPATH=src python -m enterprise_dp.cli ingest-bronze \
  --root . \
  --topic recommendation.tracking.v1 \
  --input samples/recommendation/tracking.jsonl \
  --output-dir build/recommendation-ingestion \
  --ingest-run-id local-recommendation-ingest-001

PYTHONPATH=src python -m enterprise_dp.cli build-recommendation \
  --bronze build/recommendation-ingestion/bronze/events_recommendation_tracking.jsonl \
  --upstream-manifest build/recommendation-ingestion/manifests/events_recommendation_tracking.local-recommendation-ingest-001.json \
  --output-dir build/recommendation-medallion \
  --snapshot-id local-recsys-001
```

Python entry point:

```python
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.pipelines import run_recommendation_pipeline_from_bronze

ingestion = run_bronze_ingestion(
    ".",
    "recommendation.tracking.v1",
    "samples/recommendation/tracking.jsonl",
    "build/recommendation-ingestion",
)
result = run_recommendation_pipeline_from_bronze(
    ingestion.approved_path,
    "build/recommendation-medallion",
    upstream_manifest_path=ingestion.manifest_path,
    snapshot_id="local-recsys-001",
)
```

`run_recommendation_pipeline` remains available for legacy local tests, but new work should use
approved Bronze as the input boundary.

## Outputs

The local output directory contains:

| Path | Data product |
|---|---|
| `silver/learner_activity.jsonl` | Conformed recommendation activities in the learner activity taxonomy. |
| `gold/recsys_interactions.jsonl` | ML-ready interaction rows with event weights and snapshot id. |
| `manifests/recsys_interactions.<snapshot_id>.json` | Snapshot metadata for lineage and training handoff. |

The manifest includes a top-level `row_count`, `content_hash` and `quality_passed`
for the Gold handoff, plus per-layer entries with the same fields and any
`quality_errors`. When an upstream Bronze manifest is supplied, the Gold handoff also records
`upstream_manifest_hash`, source offset ranges and `upstream_quality_passed`. If Bronze ingestion had
any quarantined records, the handoff is not publishable even when Silver and Gold row-level checks pass.

## Transform Rules

- Bronze is produced by `enterprise-dp ingest-bronze`, which validates contracts, writes approved rows
  and sends invalid records to quarantine.
- Silver maps `IMPRESSION`, `CLICK` and `ENROLLMENT` into
  `RECOMMENDATION_IMPRESSION`, `RECOMMENDATION_CLICK` and
  `RECOMMENDATION_ENROLLMENT`.
- Gold keeps publishable recommendation interactions with a non-null related course,
  excludes self-recommendations through the quality gate and assigns weights:
  `IMPRESSION=0.1`, `CLICK=1.0`, `ENROLLMENT=3.0`.

This implementation is intentionally local and deterministic. Production
orchestration can replace the JSONL reader/writer while keeping the same contract
mapping and manifest shape.
