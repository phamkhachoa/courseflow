# Enterprise Data Platform Technology Stack

Status: draft, phase-gated

## Stack By Capability

| Capability | Technology | Phase | Decision |
|---|---|---:|---|
| Event backbone | Kafka | P0 | Adopted as the enterprise event backbone. |
| Transactional event publishing | Outbox relay pattern | P0 | Required for product services that own business facts. |
| CDC | Debezium | P0 | Adopt for Bronze ingestion where state replication is needed. |
| Schema registry | Apicurio or Confluent Schema Registry | P0 | Required before production event ingestion. |
| Object storage | MinIO locally, S3/GCS/ADLS in cloud | P0 | Required lakehouse storage foundation. |
| Table format | Apache Iceberg | P0 | Preferred open table format for Bronze/Silver/Gold. |
| Batch processing | Spark | P0/P1 | For heavy Bronze-to-Silver transforms and backfill. |
| SQL transformation | dbt Core | P0/P1 | For Silver-to-Gold modeling, tests and documentation. |
| Orchestration | Dagster | P0/P1 | Preferred asset-centric orchestration. Airflow remains acceptable. |
| Catalog and lineage | DataHub or OpenMetadata | P1 | Required for enterprise governance. |
| Data quality | Great Expectations, Soda, dbt tests | P0/P1 | Required quality gates before Gold publication. |
| P0 lakehouse SQL | Trino | P0 | Lower-risk first query engine for Iceberg validation. |
| Semantic lakehouse serving | Dremio | P1/P2 | Added to stack. Adopt when semantic layer/reflections outperform Trino path. |
| Hot analytical mart | ClickHouse | P2+ | Conditional for sub-second dashboards/event analytics. |
| BI | Superset or Metabase | P1 | OSS BI over approved semantic/Gold views. |
| Feature store | Feast | P2 | Offline/online feature consistency for ML. |
| Distributed SQL / HTAP | TiDB + TiFlash | P3+ | Added to stack as conditional operational database option, not lakehouse foundation. |
| Data platform observability | Prometheus + Grafana | P0 | Extend existing observability to data SLOs. |

## Dremio Placement

Dremio is part of the stack as a candidate enterprise semantic lakehouse serving platform. It is not
required to finish P0. It becomes valuable when the group has governed Gold products and needs:

- PO/BA-facing self-service metrics.
- Semantic views over Gold data products.
- Reflections/materialized acceleration for BI dashboards.
- Governed access to Iceberg-backed lakehouse data.

## TiDB Placement

TiDB is part of the stack as a future distributed SQL/HTAP option. It is not a replacement for the
lakehouse and should not replace product service databases without a measured operational reason.

Use TiDB only when a specific enterprise product service needs:

- MySQL-compatible distributed SQL.
- Horizontal OLTP scale beyond what the current operational database can handle.
- Real-time HTAP on the same operational dataset via TiFlash.
- A dedicated migration plan and production SLO evidence.

## Current SA Guardrail

Adding Dremio and TiDB to the stack does not mean adding them to P0 runtime. P0 remains focused on
contracts, product onboarding, ingestion, Bronze/Silver/Gold, quality gates, catalog metadata and
reproducibility.
