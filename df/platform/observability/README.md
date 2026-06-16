# Data Observability Platform

Data observability covers pipeline health and data product trust, separate from service liveness.

## Production Gate Spec

The production SLO and release gate policy lives in
[production-slo-release-gates.md](production-slo-release-gates.md). It defines the P0 gates for:

- Ingestion lag for `recommendation.tracking.v1`.
- Bronze, Silver and Gold freshness.
- Blocking data quality failures and quarantine triage.
- Contract and schema compatibility.
- Gold publish evidence for `gold.recsys_interactions`.

## Core Signals

- Ingestion lag by topic and source.
- Bronze/Silver/Gold freshness.
- Rejected row and quarantine counts.
- Data quality failures by product and check.
- Schema compatibility failures.
- Gold publish timestamp and snapshot id.
- ML feature freshness and training dataset reproducibility.

## Local Metrics Export

`enterprise-df observability-export` converts catalog bundles and release evidence into:

- Prometheus text metrics for CI, local collectors or future push/pull integration.
- A JSON operations summary that keeps high-cardinality identifiers such as release ids, hashes,
  manifest paths and snapshot ids out of metric labels.

```bash
enterprise-df observability-export \
  --catalog build/catalog/catalog-bundle.json \
  --release-evidence build/evidence/use-case.finance.json \
  --output-metrics build/observability/enterprise-df.prom \
  --output-summary build/observability/enterprise-df-summary.json \
  --environment local
```

Metric labels are intentionally stable: `environment`, `product`, `domain`, `layer`, `pipeline`,
`use_case`, `gate_id`, `topic` and `data_product`. High-cardinality values belong in the JSON
summary and release evidence store, not Prometheus labels.
