# Runtime Lineage Export

`enterprise-df openlineage-export` converts a catalog bundle with run manifests into OpenLineage-style
JSONL run events. This is the P0 bridge from local metadata-as-code to a future lineage backend such
as Marquez, DataHub, OpenMetadata or an internal collector.

The exporter is read-only. It does not publish directly to a remote backend, does not rewrite
manifests and does not include raw payloads or direct PII in event facets.

## Example

```bash
enterprise-df catalog-export \
  --root . \
  --output build/catalog/catalog-bundle.json \
  --manifest build/ingestion/manifests/events.json \
  --manifest build/pipeline/manifests/gold.json

enterprise-df openlineage-export \
  --catalog build/catalog/catalog-bundle.json \
  --output build/lineage/openlineage-events.jsonl \
  --namespace enterprise-df://local
```

## Event Contents

- `eventType=COMPLETE` when `quality_passed=true`; otherwise `FAIL`.
- `run.runId` is deterministic from the enterprise run URN.
- `job.namespace` and dataset namespaces are environment-aware through `--namespace`.
- Inputs and outputs are derived from runtime manifests, not only static catalog lineage.
- Custom `enterpriseDf_*` facets carry manifest hash, product/domain/layer, quality status, source
  positions and dataset governance metadata.

## Production Guardrails

- Emit lineage asynchronously from saved artifacts; do not make pipeline success depend on a remote
  lineage sink.
- Keep raw event payloads out of lineage facets.
- Use production namespaces such as `enterprise-df://prod` to avoid mixing local/staging/prod graphs.
- Store the JSONL artifact and hash in the release record before publishing to a remote collector.
- Attach the OpenLineage JSONL artifact to `enterprise-df catalog-publish-manifest` before any
  staging or production catalog publish.
