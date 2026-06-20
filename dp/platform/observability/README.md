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

The operations artifact for those gates lives in
[quality-slo-release-gates-ops.md](quality-slo-release-gates-ops.md). It defines
`quality_slo_release_gates_ops_report.v1`, the CLI, the runtime quality evidence contract and the
alert evidence contract that Control Tower consumes for production signoff.
The local `enterprise-dp live-quality-slo-smoke` command now produces this evidence over the
published finance Gold Iceberg table through Trino and is part of `make ci`; production still needs
managed quality exporters and Alertmanager/PagerDuty evidence.

## Core Signals

- Ingestion lag by topic and source.
- Bronze/Silver/Gold freshness.
- Rejected row and quarantine counts.
- Data quality failures by product and check.
- Schema compatibility failures.
- Gold publish timestamp and snapshot id.
- ML feature freshness and training dataset reproducibility.

## Local Metrics Export

`enterprise-dp observability-export` converts catalog bundles and release evidence into:

- Prometheus text metrics for CI, local collectors or future push/pull integration.
- A JSON operations summary that keeps high-cardinality identifiers such as release ids, hashes,
  manifest paths and snapshot ids out of metric labels.

```bash
enterprise-dp observability-export \
  --catalog build/catalog/catalog-bundle.json \
  --release-evidence build/evidence/use-case.finance.json \
  --output-metrics build/observability/enterprise-dp.prom \
  --output-summary build/observability/enterprise-dp-summary.json \
  --environment local
```

Metric labels are intentionally stable: `environment`, `product`, `domain`, `layer`, `pipeline`,
`use_case`, `gate_id`, `topic` and `data_product`. High-cardinality values belong in the JSON
summary and release evidence store, not Prometheus labels.

## Incident And SLO Operations

`enterprise-dp quality-slo-release-gates-ops-report` writes a
`quality_slo_release_gates_ops_report.v1` from catalog, release evidence, runtime quality evidence,
alert evidence and optional incident/SLO report artifacts.

```bash
enterprise-dp quality-slo-release-gates-ops-report \
  --root . \
  --environment prod \
  --catalog build/catalog/catalog-bundle.json \
  --release-evidence build/evidence/release-prod.json \
  --quality-runtime-evidence build/evidence/quality-runtime-prod.json \
  --alert-evidence build/evidence/slo-alerts-prod.json \
  --incident-report build/observability/incidents-prod.json \
  --output build/evidence/quality-slo-release-gates-ops-prod.json
```

`enterprise-dp incident-report` converts a `data_product_control_tower_report.v1` into an
`incident_slo_report.v1`. The report is the bridge from passive data observability to an operator
queue: every Control Tower blocker becomes a deterministic incident fingerprint with severity,
owner, assignee, SLA target, SLA age, escalation flag, runbook and linked evidence.

```bash
enterprise-dp control-tower-report \
  --root . \
  --output build/control-tower/report.json

enterprise-dp incident-report \
  --control-tower-report build/control-tower/report.json \
  --incident-registry governance/incidents.yaml \
  --output build/observability/incidents.json
```

The optional `governance/incidents.yaml` registry preserves human state such as assignee,
acknowledgement, investigation status and custom SLA target. CI/SRE automation should fail closed
when the incident report has open P0 incidents or breached SLA items, then page the owner queues
listed in `decision_board.page_now`.
