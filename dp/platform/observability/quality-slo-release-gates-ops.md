# Quality/SLO Release Gates Operations Report

`quality_slo_release_gates_ops_report.v1` is the operations gate for the
`quality-slo-release-gates` P0 capability. It gives Control Tower one artifact-backed decision for
data quality, freshness, release evidence and SLO alert state across all enterprise data products.

The report is product-agnostic. LMS recommendation assets are only the first onboarded examples; the
same contract applies to finance, customer, workforce, risk, ML feature and future group products.

## Command

```bash
enterprise-dp quality-slo-release-gates-ops-report \
  --root . \
  --environment prod \
  --catalog build/catalog/catalog-bundle.json \
  --release-evidence build/evidence/release-enterprise-kpi-prod.json \
  --quality-runtime-evidence build/evidence/quality-runtime-prod.json \
  --alert-evidence build/evidence/slo-alerts-prod.json \
  --incident-report build/observability/incidents-prod.json \
  --output build/evidence/quality-slo-release-gates-ops-prod.json
```

For `local`, the command can run as a repository preflight without runtime evidence. For `staging`
and `prod`, it fails closed unless release evidence, runtime quality evidence and alert evidence are
attached and passing.

## Local Live Proof

`enterprise-dp live-quality-slo-smoke` is the current local runtime proof for this capability. It
reads `orchestrated_live_publication_report.v1`, queries the published
`gold.finance_benefit_reconciliation` Iceberg table through Trino, writes
`quality_runtime_evidence.v1`, writes green `slo_alert_evidence.v1`, generates
`quality_slo_release_gates_ops_report.v1` and emits `live_quality_slo_smoke_report.v1`.

The smoke is part of `make ci` and can be attached to `production-review-pack` through
`--live-quality-slo-smoke-report`. A passing report removes the local partner-review blocker for
`quality-slo-release-gates`, but it does not claim production coverage for managed
Great Expectations/Soda/dbt runner rollout, production Alertmanager/PagerDuty routing, multi-product
runtime-quality rollout or production burn-rate monitoring.

The smoke also runs negative controls: corrupt Gold required fields, stale freshness, red alert
state, environment mismatch and missing production-like alert evidence must all fail closed.

## Input Artifacts

| Input | Required in local | Required in staging/prod | Purpose |
|---|---:|---:|---|
| `catalog_bundle.v1` | Optional | Yes in release flow | Lists data products, quality declarations, ownership and contracts. |
| Release evidence JSON | Optional | Yes | Proves `P0-INGESTION-LAG`, `P0-FRESHNESS`, `P0-PIPELINE-QUALITY`, `P0-QUALITY-PROFILE`, `P0-OUTPUT-EVIDENCE` and release profile gates. |
| `quality_runtime_evidence.v1` | Optional | Yes | Adapter output from Great Expectations, Soda, dbt tests or equivalent runtime quality checks. |
| `slo_alert_evidence.v1` | Optional | Yes | Export from Prometheus/Alertmanager/SRE alert state proving P0 alerts are green. |
| `incident_slo_report.v1` | Optional | Optional | Open incident/SLO queue generated from Control Tower blockers. |

## Runtime Quality Evidence Contract

The runtime quality adapter must emit a local JSON artifact before the ops report can pass in
production-like environments.

```json
{
  "artifact_type": "quality_runtime_evidence.v1",
  "environment": "prod",
  "synthetic": false,
  "generated_at": "2026-06-16T10:00:00Z",
  "passed": true,
  "summary": {
    "failed_check_count": 0,
    "freshness_breach_count": 0
  },
  "data_products": [
    {
      "data_product": "gold.recsys_interactions",
      "quality_tool": "great_expectations",
      "validation_passed": true,
      "failed_check_count": 0,
      "freshness_status": "GREEN",
      "age_seconds": 120,
      "slo_seconds": 14400,
      "quarantine_row_count": 0
    }
  ]
}
```

The first production implementation can wrap Great Expectations or Soda results, but the DP contract
does not depend on a single vendor. The important boundary is the evidence shape, environment,
freshness numbers and stable data product name.

## Alert Evidence Contract

`slo_alert_evidence.v1` is the SRE-facing side of the same gate. It must prove no open P0 incident
or breached SLA is hidden from release signoff.

```json
{
  "artifact_type": "slo_alert_evidence.v1",
  "environment": "prod",
  "generated_at": "2026-06-16T10:00:00Z",
  "status": "green",
  "summary": {
    "open_p0_incident_count": 0,
    "sla_breached_count": 0
  }
}
```

## Pass Conditions

- The target environment is `local`, `staging` or `prod`.
- The catalog bundle is present and hash-bound.
- For `staging` and `prod`, at least one release evidence artifact is attached.
- Release evidence environment matches the report environment.
- Production-like release evidence passes quality and freshness gates.
- `quality_runtime_evidence.v1` is present, non-synthetic and passing for production-like
  environments.
- Runtime freshness is `GREEN` and `age_seconds <= slo_seconds` whenever both values are present.
- Runtime failed check count is zero.
- `slo_alert_evidence.v1` is present and green for production-like environments.
- Optional incident report has no open P0 incident or breached SLA.
- Gold data products have quality profile coverage.

## Control Tower Consumption

`enterprise-dp control-tower-report` consumes the report through
`--quality-slo-release-gates-ops-report`. Control Tower blocks production signoff when the artifact
type is invalid, the environment does not match, the readiness state is wrong, the report is failing
or any data product has quality/SLO release issues.

The local Control Tower runner can generate a local preflight report from the repository when the
artifact is not supplied. Production-like signoff must pass an explicit artifact from the release
workspace.

## Current Maturity

Current registry level remains `L1` until production runtime exporters and alerting are connected.
For partner review, the local finance slice now has a live Trino/Iceberg quality/SLO proof with
negative controls. The remaining enterprise hardening is to connect production exporters:

- Great Expectations/Soda/dbt runtime results into `quality_runtime_evidence.v1`.
- Prometheus/Alertmanager/SRE status into `slo_alert_evidence.v1`.
- Multi-product rollout across all P0 Gold outputs.
- Production burn-rate and incident-routing evidence.
- CI/CD and release promotion enforcement for production `quality_slo_release_gates_ops_report.v1`.
