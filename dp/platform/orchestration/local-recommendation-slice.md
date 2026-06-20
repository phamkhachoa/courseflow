# Local Recommendation Slice Orchestration

This runbook defines the local P0 slice used to prove the enterprise DP operating pattern:
contracted ingestion, Medallion build, catalog export and release-gate evidence.

CourseFlow LMS is only the first product using the pattern. New enterprise products should reuse the
same control points: source contract, Bronze idempotency, Silver/Gold quality, catalog lineage and
release evidence.

## Preferred Generic Command

Use this path for new enterprise use cases. The runner, input topic, input data product, output data
products and primary output are resolved from `use-cases/registry.yaml`.

```bash
PYTHONPATH=src python -m enterprise_dp.cli run-use-case \
  --root . \
  --use-case-id ml-feature-governance \
  --input samples/recommendation/tracking.jsonl \
  --output-dir /tmp/enterprise-dp/ml-feature-governance \
  --release-id local-ml-feature-001 \
  --environment local
```

Finance reconciliation uses the same generic entrypoint:

```bash
PYTHONPATH=src python -m enterprise_dp.cli run-use-case \
  --root . \
  --use-case-id finance-benefit-reconciliation \
  --input samples/finance/benefit_settled.jsonl \
  --output-dir /tmp/enterprise-dp/finance-benefit-reconciliation \
  --release-id local-finance-recon-001 \
  --environment local
```

## Backward-Compatible Pilot Command

```bash
PYTHONPATH=src python -m enterprise_dp.cli run-recommendation-slice \
  --root . \
  --input samples/recommendation/tracking.jsonl \
  --output-dir /tmp/enterprise-dp/recommendation-slice \
  --release-id local-recsys-001 \
  --environment local
```

The command writes:

- `ingestion/bronze/`: approved Bronze JSONL.
- `ingestion/quarantine/`: rejected records with reason codes.
- `ingestion/manifests/`: source position, schema and quality manifest.
- `pipeline/`: runner outputs such as Silver/Gold datasets and the pipeline manifest.
- `catalog/catalog-bundle.json`: metadata and lineage bundle for DataHub/OpenMetadata style targets.
- `evidence/schema-registry.<release-id>.json`: local schema compatibility report for local/dev
  release gates.
- `evidence/access-policy.<release-id>.json`: local access-policy report for Gold serving controls.
- `evidence/use-case.<use-case-id>.<release-id>.json`: generic use-case release gate evidence pack.

The legacy `run-recommendation-slice` command writes the same control artifacts under the older
`medallion/` and `recommendation-slice.*.json` names.

## Release Gates

Generic use-case evidence blocks publication unless these P0 controls pass:

- `P0-CONTRACT-COMPATIBILITY`: project structure, topic contracts, data-product contracts, product
  onboarding and domain registry validate.
- `P0-SCHEMA-REGISTRY-COMPATIBILITY`: schema registry report exists and passes, or production
  evidence provides a durable external URI plus hash.
- `P0-ACCESS-POLICY`: access-policy report exists and passes, or production evidence provides a
  durable external URI plus hash.
- `P0-RETENTION-ERASURE`: retention and erasure report exists and passes. Local/dev may generate
  synthetic evidence, but production-like releases must use external retention job evidence or an
  external evidence attestation. `run-use-case` and `run-recommendation-slice` accept
  `--retention-evidence-input` to generate the release report from a real
  `retention_erasure_job_evidence.v1` document.
- `P0-PRODUCTION-EVIDENCE`: staging/prod releases require commit SHA, schema registry report,
  schema registry report hash, validator output, access-policy check id, access-policy report URI
  and hash, access-grant evidence, retention evidence, lakehouse snapshot evidence and approver.
- `P0-PIPELINE-QUALITY`: ingestion and runner manifests passed, with no quarantine rows when Bronze
  ingestion is part of the use-case flow.
- `P0-OUTPUT-EVIDENCE`: the declared primary output and output data products have snapshot id,
  row-count and content-hash evidence.
- `P0-LAKEHOUSE-SNAPSHOT-EVIDENCE`: local/dev passes without external snapshot evidence for fast
  iteration; staging/prod requires `lakehouse_snapshot_evidence.v1` that binds the candidate
  Silver/Gold outputs to Iceberg snapshot metadata and the upstream Bronze offset ledger.
- `P0-CATALOG-LINEAGE`: catalog bundle contains use-case, static data-product and run evidence.
- `P0-RELEASE-EVIDENCE-PROFILE`: the active release evidence profile applies to the use case,
  required gates are present and passed, and required artifact hashes are attached.

The backward-compatible recommendation pilot evidence also checks recommendation-specific gates:

- `P0-INGESTION-LAG`: approved records landed within the topic freshness SLO.
- `P0-FRESHNESS`: Bronze, Silver and Gold assets are fresh against their data-product SLOs.
- `P0-QUALITY`: ingestion and Medallion manifests passed, with no quarantine rows.
- `P0-GOLD-EVIDENCE`: Gold snapshot has source positions, hashes, upstream manifest hash and run
  evidence.
- `P0-CATALOG-LINEAGE`: catalog bundle contains static and run lineage.

## Production Mapping

In production, Dagster or Airflow should invoke equivalent assets/operators. Dremio reads governed
Iceberg Gold/Silver datasets for BI and exploration. TiDB is reserved for low-latency serving state
that needs transactional access and should consume only published Gold outputs or model-serving
materializations.
