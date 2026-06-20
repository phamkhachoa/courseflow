# Shared Data Platform Capabilities

`platform/` contains shared capabilities owned by the data platform team. Domain teams should consume
these capabilities through contracts, templates and paved-road tooling rather than creating bespoke
pipeline infrastructure per use case.

## Capability Boundaries

| Path | Owns |
|---|---|
| `ingestion/` | Kafka, outbox, CDC, batch connector specs and source onboarding rules. |
| `lakehouse/` | Bronze/Silver/Gold table standards, partitioning, retention and storage conventions. |
| `processing/` | Spark/dbt/Flink transformation standards, backfills and materialization patterns. |
| `orchestration/` | Dagster/Airflow asset definitions, schedules, retries and backfill controls. |
| `quality/` | Reusable data quality checks, quarantine rules and quality gate policy. |
| `governance/` | Catalog, lineage, ownership, glossary and policy metadata integration. |
| `serving/` | Lakehouse SQL, semantic layer, hot marts, BI and ML serving handoff. |
| `observability/` | Data SLO metrics, alerts, runbooks and release evidence. |
| `security/` | Tenant isolation, masking, secrets, access audit and retention enforcement. |
| `developer-experience/` | Templates, local tooling, CI checks and onboarding paved roads. |
| `environments/` | Local, staging and production environment overlays. |
| `runtime/` | Runtime topology, IaC profile metadata and local/staging/prod readiness gates. |
| `capabilities/` | Capability maturity registry and production readiness report inputs. |
| `control-tower/` | P0 Data Product Control Tower operating model and production signoff report. |

## SA Rule

Domain-specific business meaning lives under `domains/<domain>/`. Shared engines, reusable policies
and platform-level operations live here.
