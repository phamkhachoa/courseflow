# Reference Model Benchmark

This benchmark captures external architecture patterns used to shape the group enterprise data
platform. It is not a vendor lock-in decision; it is the rationale behind the platform guardrails.

## Patterns Adopted

| Reference | Pattern Adopted | Platform Decision |
|---|---|---|
| [Databricks Medallion Architecture](https://www.databricks.com/blog/what-is-medallion-architecture) and [Azure Databricks Medallion docs](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion) | Progressive Bronze, Silver and Gold data quality layers. | Keep Medallion as the lakehouse modeling backbone. Bronze is immutable/source-aligned, Silver is conformed, Gold is business-ready and ML/BI-safe. |
| [Google Cloud Cortex Framework](https://cloud.google.com/solutions/cortex) and [Cortex Data Platform](https://github.com/GoogleCloudPlatform/cortex-data-foundation) | Packaged data platform and reusable business accelerators. | Maintain a group-wide use-case/data-product portfolio, not only product-local pipelines. |
| [Netflix Data Mesh platform](https://netflixtechblog.com/data-mesh-a-data-movement-and-processing-platform-netflix-1288bcab2873) | General-purpose data movement/processing platform with clear source ownership. | Products publish governed events/CDC/batch feeds; DP owns reusable movement, lakehouse and governance controls. |
| [Airbnb Minerva metrics platform](https://medium.com/airbnb-engineering/how-airbnb-achieved-metric-consistency-at-scale-f23cc53dea70) | Centralized, consistent metrics for analytics, reporting and experimentation. | Enterprise metrics belong in governed semantic/Gold definitions, not duplicated inside product dashboards. |
| [DataHub features](https://docs.datahub.com/docs/features) and [OpenMetadata](https://open-metadata.org/) | Catalog, lineage, discovery, governance and observability. | Catalog bundle exports products, domains, use cases, contracts, lineage and run evidence before runtime catalog integration. |
| [dbt Semantic Layer](https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl) | Central metric definitions for downstream tools. | Semantic metrics are a platform capability tied to certified Gold data products and use-case owners. |
| [Dremio Iceberg docs](https://docs.dremio.com/current/developer/data-formats/apache-iceberg/) | Open table format query serving over Iceberg. | Dremio remains a P1/P2 semantic lakehouse candidate after Gold products stabilize; Trino remains P0. |
| [TiDB overview](https://docs.pingcap.com/tidb/stable/overview) and [TiDB HTAP docs](https://docs.pingcap.com/tidb/stable/explore-htap/) | MySQL-compatible distributed SQL and HTAP for operational use cases. | TiDB is a conditional operational/HTAP option, not the lakehouse foundation. |

## Architecture Consequences

- Use cases are first-class platform artifacts because enterprise value is measured by reusable
  data products and metrics, not by the number of pipelines.
- Data contracts and source-position evidence are required before data reaches Bronze.
- Gold publication requires quality, freshness, lineage and access-policy evidence.
- BI, ML and reverse ETL consume approved Gold, semantic or feature layers only.
- Query/serving engines are phase-gated: Trino first, Dremio only after POC superiority, TiDB only
  for measured operational needs.
