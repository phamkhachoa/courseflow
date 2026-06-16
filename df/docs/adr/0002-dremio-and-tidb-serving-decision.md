# ADR 0002: Dremio and TiDB Fit for Enterprise Data Platform

Status: Accepted
Date: 2026-06-16

## Context

The initial enterprise data platform stack proposed Trino or ClickHouse as the OLAP serving layer.
The team asked whether Dremio and TiDB are a better fit and whether they should replace any selected
technology.

The target platform is an enterprise lakehouse:

- Kafka/outbox/CDC ingestion.
- Bronze/Silver/Gold products on object storage with Iceberg or a similar table format.
- Governance, quality gates, lineage and ML handoff from Gold snapshots.
- Self-service BI and semantic metrics for learning, finance, customer, workforce, product analytics and
  enterprise reporting.

## Decision

Do not introduce Dremio or TiDB in P0.

Use Trino as the P0 lakehouse SQL query layer because it is lighter operationally and fits the first
Iceberg/MinIO validation path while the first product slice still lacks schema registry enforcement, Bronze sinks,
quality-gated Gold publication and catalog/lineage.

Evaluate Dremio in P1 and adopt it only if its semantic layer and Reflections are demonstrably
superior to the Trino + dbt/DataHub/Superset path for the group's self-service BI and enterprise
reporting use cases. If adopted, Dremio should replace the Trino serving tier for those workloads
rather than running as a duplicate default path.

Keep ClickHouse as an optional hot mart, not the default semantic/lakehouse serving tier.

Do not adopt TiDB for the P0/P1 data platform. Keep TiDB as a future, case-by-case option for a
specific operational service or MySQL-compatible distributed OLTP/HTAP requirement.

Dremio and TiDB are both listed in the enterprise data platform technology stack, but with different
phase gates: Dremio as a P1/P2 semantic lakehouse candidate, TiDB as a P3+ operational HTAP option.

## Why Dremio Is Conditional

Dremio can be superior to a bare Trino-first path once the group has real governed Gold products,
because business teams will need self-service analytics over those products, not just a
federated SQL engine.

Selected advantages:

- Native lakehouse/Apache Iceberg query serving and catalog integration.
- Semantic layer through virtual datasets and curated business views.
- Reflections/materialized acceleration for BI workloads.
- Useful bridge between Gold lakehouse products and BI/AI consumers.

This makes Dremio a strong P1/P2 candidate for enterprise reporting and semantic analytics if the
team is willing to operate its runtime and model semantic objects as code. It is not a P0 dependency.

## Why ClickHouse Stays Optional

ClickHouse is still excellent for hot analytical marts, high-cardinality event analytics and
predictable sub-second dashboards. It should be introduced only when a specific Gold product has
query patterns that Dremio/reflections cannot meet cost-effectively.

## Why TiDB Does Not Fit P0/P1

TiDB is a strong distributed SQL database with MySQL compatibility, horizontal scale and HTAP
capabilities via TiFlash. Those strengths do not directly solve the platform's immediate
gap:

- The first CourseFlow LMS product slice is already PostgreSQL-oriented and database-per-service.
- The data platform must decouple BI/ML from OLTP, not introduce a new OLTP serving database.
- TiDB does not replace lakehouse governance, Bronze/Silver/Gold history, object storage time travel,
  data contracts or feature-store handoff.
- Migrating services from Postgres to TiDB would be a large product-platform migration with little
  payoff for the current data platform phase.

TiDB can be revisited if any group product later has a MySQL-compatible service requiring horizontal
OLTP scale plus real-time HTAP on the same operational data, but it is not the enterprise lakehouse
foundation.

## Adoption Conditions for Dremio

Dremio may replace the P0 Trino serving path only if these conditions are met:

- Gold products are backed by Iceberg or another governed table format.
- Dremio semantic views are versioned, reviewed and deployed through DataOps.
- Reflections have freshness SLOs and alerting.
- Dremio access is integrated with enterprise identity and row/column security policy.
- Catalog and lineage are published to DataHub/OpenMetadata or equivalent.
- BI tools connect through approved semantic views, not arbitrary Bronze/Silver tables.
- A POC proves query performance, reflection freshness and tenant isolation against at least
  `gold.recsys_interactions` and one learner-success or enterprise-reporting Gold product.

## Consequences

Positive:

- Clear semantic serving tier for PO/BA-facing analytics.
- Less need to build a separate semantic layer immediately.
- Better BI acceleration path over lakehouse Gold products.
- Trino remains the lower-risk P0 query path and can remain a fallback if Dremio is adopted later.

Tradeoffs:

- Adds a stateful serving platform to operate.
- Semantic views/reflections must be governed as code.
- Dremio does not remove the need for Spark/dbt/Dagster/DataHub/quality gates.
- ClickHouse may still be needed for some hot marts.

## External Evidence

- Dremio documents support for Iceberg REST catalogs and lakehouse catalogs.
- Dremio Reflections are query acceleration structures similar to materialized views.
- Dremio positions virtual datasets/semantic layer as a self-service analytics layer.
- TiDB documentation describes it as a MySQL-compatible distributed SQL HTAP database with TiKV and
  TiFlash; useful for distributed OLTP/HTAP, not a replacement for an enterprise lakehouse.
