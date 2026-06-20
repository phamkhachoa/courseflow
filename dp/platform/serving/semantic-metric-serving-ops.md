# Semantic Metric Serving Operations Report

`semantic_metric_serving_ops_report.v1` is the operations gate for the
`semantic-metric-serving` P0 capability. It checks that governed metrics can move from registry to
queryable semantic views with lifecycle, deployment and usage evidence.

The gate is product-agnostic: finance, customer, compliance, LMS and future group products all use
the same semantic metric registry and serving evidence contract.

## Command

```bash
enterprise-dp semantic-metric-serving-ops-report \
  --root . \
  --environment prod \
  --semantic-view-manifest build/serving/semantic-views.json \
  --metric-certification-report build/evidence/semantic-metric-certification-prod.json \
  --serving-deployment-evidence build/evidence/semantic-serving-deployment-prod.json \
  --usage-evidence build/evidence/semantic-metric-usage-prod.json \
  --output build/evidence/semantic-metric-serving-ops-prod.json
```

For `local`, the report can run as a repository preflight by building the semantic view manifest from
`platform/serving/semantic-metrics.yaml`. For `staging` and `prod`, it fails closed unless an
explicit `semantic_views_manifest.v1`, `semantic_metric_certification_report.v1`, deployment
evidence and usage evidence are attached.

Generate certification evidence with:

```bash
enterprise-dp semantic-metric-certification-report \
  --root . \
  --environment prod \
  --output build/evidence/semantic-metric-certification-prod.json
```

## Input Artifacts

| Input | Required in local | Required in staging/prod | Purpose |
|---|---:|---:|---|
| `semantic-metrics.yaml` | Yes | Yes | Governed metric definitions, owners, lifecycle status, source Gold products and serving names. |
| `semantic-metric-certifications.yaml` | Yes | Yes | Maker-checker certification ledger with approval, reason, evidence, diff and impact analysis. |
| `semantic_views_manifest.v1` | Generated if omitted | Yes | Trino/Dremio SQL manifest hash-bound to the metric registry. |
| `semantic_metric_certification_report.v1` | Generated if omitted | Yes | Report proving certified metrics have approved maker-checker certification evidence. |
| `semantic_serving_deployment_evidence.v1` | Optional | Yes | Query-engine apply and smoke-test evidence for each semantic view. |
| `semantic_metric_usage_evidence.v1` | Optional | Yes | BI/app usage telemetry evidence for certified metric consumption. |

## Certification Evidence Contract

`governance/semantic-metric-certifications.yaml` records approved certification batches. Each
certification must include metric ids, requester, approver, approver role, reason, evidence URIs,
diff fields and impact analysis across use cases, consumers and source Gold products. The report
blocks maker-checker self-approval, missing formula/source/quality/impact evidence and incomplete
impact coverage.

## Deployment Evidence Contract

```json
{
  "artifact_type": "semantic_serving_deployment_evidence.v1",
  "environment": "prod",
  "generated_at": "2026-06-16T10:00:00Z",
  "semantic_view_manifest_hash": "sha256:...",
  "passed": true,
  "summary": {
    "view_count": 62,
    "failed_view_count": 0
  },
  "views": [
    {
      "metric_id": "revenue_net",
      "engine": "trino",
      "view_name": "semantic.enterprise_metrics.revenue_net",
      "deployed": true,
      "smoke_test_passed": true,
      "access_policy_checked": true
    }
  ]
}
```

The first P0 serving path is Trino. Dremio views can be included in the same manifest, but Dremio is
still a P1/P2 candidate until a group-wide POC proves it should become a production semantic layer.

## Usage Evidence Contract

```json
{
  "artifact_type": "semantic_metric_usage_evidence.v1",
  "environment": "prod",
  "generated_at": "2026-06-16T10:00:00Z",
  "passed": true,
  "summary": {
    "metric_count": 31,
    "usage_tracking_disabled_count": 0
  },
  "metrics": [
    {
      "metric_id": "revenue_net",
      "usage_tracking_enabled": true,
      "active_consumer_count": 3,
      "last_queried_at": "2026-06-16T09:55:00Z"
    }
  ]
}
```

## Pass Conditions

- Semantic metric registry is present and valid.
- Every metric is bound to an approved Gold data product through the registry validator.
- Local reports allow `provisional` or `certified` metrics.
- Production-like reports require every metric to be `certified`.
- Certified metrics require an approved `semantic_metric_certification_report.v1` with separated
  requester and approver, reason, evidence, diff and impact analysis.
- The semantic view manifest is valid and hash-bound to the registry.
- Production-like reports use an explicit manifest artifact, not an implicit generated manifest.
- Production-like reports use an explicit certification report artifact, not an implicit generated
  report.
- Deployment evidence is present, environment-matched, manifest-hash matched and passing.
- Every manifest view is deployed, smoke-tested and access-policy checked.
- Usage evidence is present, environment-matched and usage tracking is enabled per certified metric.

## Control Tower Consumption

`enterprise-dp control-tower-report` consumes the report through
`--semantic-metric-serving-ops-report`. Control Tower blocks production signoff when the artifact
type is invalid, the environment does not match, the readiness state is wrong, the report is failing
or any metric has lifecycle, manifest, deployment or usage tracking issues.

`enterprise-dp production-review-pack` can attach the same artifact through
`--semantic-metric-serving-ops-report`. The review pack removes the `semantic-metric-serving` P0
capability blocker only for a staging/prod report with `readiness_state=production_like_ready`,
`mode=runtime_attested`, certified and approved metrics, explicit semantic view manifest, passing
deployment evidence, usage evidence and zero failed checks/metrics. A local preflight report can
pass and support partner review, but it never closes the production capability blocker.

## Current Maturity

Current level remains `L1`: registry validation, semantic view generation, artifact-backed ops
report, maker-checker certification workflow, tests and Control Tower blocker are implemented.
Remaining L3 work:

- Publish Trino semantic views to staging/prod and persist deployment evidence.
- Export BI/query usage telemetry into `semantic_metric_usage_evidence.v1`.
- Decide Dremio production role only after POC evidence beats the Trino baseline.
