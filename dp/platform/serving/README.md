# Serving Platform

Serving owns how governed Gold data products are queried and activated by humans, BI tools, ML and
operational systems.

## Decision

Trino is the P0 lakehouse SQL serving path because it is the lower-risk way to validate
Iceberg-backed Gold products while the platform foundation is still being built.

Dremio is a P1/P2 candidate for the lakehouse semantic layer. It should replace the Trino serving path
for BI/self-service analytics only if a POC proves its value is superior for group-wide workloads. Its candidate
advantages are:

- Iceberg lakehouse query serving.
- Virtual datasets and semantic layer.
- Reflections/materializations for BI acceleration.
- Lakehouse catalog integration.

ClickHouse remains an optional hot serving mart for very high-concurrency, low-latency dashboards or
event analytics where denormalized Gold extracts need sub-second predictable performance.

TiDB is not part of the P0/P1 data platform serving path. It is a distributed SQL/HTAP database, not
the lakehouse serving layer the platform currently needs.

## Serving Tiers

| Tier | Preferred Technology | Use |
|---|---|---|
| P0 lakehouse SQL | Trino | Gold data products and ad-hoc SQL validation. |
| P1/P2 semantic lakehouse candidate | Dremio | BI semantic views and accelerated self-service analytics if POC passes. |
| Hot dashboard mart | ClickHouse, only when justified | High-concurrency dashboards over curated extracts. |
| Operational read model | Existing backend services | Product APIs and operational UX. |
| ML feature serving | Feast later | Offline/online feature consistency. |
| Future operational HTAP | TiDB + TiFlash | Only for a measured service-level OLTP/HTAP need. |

## Rules

- Serving tools read Gold or approved semantic views, not OLTP service databases.
- Cross-engine serving compatibility is now locally smoke-tested for Trino plus PyIceberg against
  the shared Postgres JDBC Iceberg catalog through `enterprise-dp catalog-cross-engine-smoke`.
  Production sign-off still needs managed catalog HA, failover and backup/restore evidence.
- Semantic definitions must be versioned and reviewed like code. `semantic-metrics.yaml` is the
  registry for governed metric definitions, source Gold products, dimensions, filters and Trino or
  Dremio serving names.
- Certified metrics must be backed by `governance/semantic-metric-certifications.yaml` and
  `semantic_metric_certification_report.v1`, including maker-checker approval, reason, evidence,
  diff and use-case/consumer/source impact analysis.
- `enterprise-dp semantic-views-export` renders the metric registry into a deployable
  `semantic_views_manifest.v1` with Trino and/or Dremio `CREATE OR REPLACE VIEW` SQL.
- `enterprise-dp semantic-metric-certification-report` validates metric certification evidence and
  writes `semantic_metric_certification_report.v1`.
- `enterprise-dp semantic-metric-serving-ops-report` writes
  `semantic_metric_serving_ops_report.v1` from the metric registry, certification report, semantic
  view manifest, deployment evidence and usage evidence. Control Tower consumes this as the P0
  semantic serving gate; local can run as preflight, while staging/prod fail closed without explicit
  evidence.
- Reflections/materializations must be tied to data freshness SLOs.
- Any hot mart must declare its source Gold product and reverse lineage.

## Operations Gate

The semantic serving operations contract lives in
[semantic-metric-serving-ops.md](semantic-metric-serving-ops.md). It intentionally proves artifact
readiness, not live BI integration by itself. Metric certification now has a maker-checker
control-plane workflow; production still needs query-engine deployment jobs, smoke tests, access
checks and usage telemetry exporters to emit the required evidence.
