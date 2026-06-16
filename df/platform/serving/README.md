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
- Semantic definitions must be versioned and reviewed like code. `semantic-metrics.yaml` is the
  registry for governed metric definitions, source Gold products, dimensions, filters and Trino or
  Dremio serving names.
- `enterprise-df semantic-views-export` renders the metric registry into a deployable
  `semantic_views_manifest.v1` with Trino and/or Dremio `CREATE OR REPLACE VIEW` SQL.
- Reflections/materializations must be tied to data freshness SLOs.
- Any hot mart must declare its source Gold product and reverse lineage.
