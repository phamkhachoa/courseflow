# Council 0054: Model Serving Metrics Export

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The AI Platform now persists a model-serving metrics export and consumes it in the operating cockpit. Serving health is no longer blocked by missing metrics; the cockpit projects the hosted serving adapter as `healthy` when request, success and audit counters are consistent.

The platform added:

- `platform/src/courseflow_ai_platform/serving_metrics_export.py`
- `platform/operations/reports/model-serving-metrics-export-v1.yaml`
- `platform/tests/test_serving_metrics_export.py`
- CLI flag `--write-model-serving-metrics-export-report`
- operating cockpit default loading of the metrics export snapshot

## Current Serving Metrics Export

| Scope | Value |
|---|---|
| Export status | `connected` |
| Source adapter | `hosted-model-serving-adapter` |
| Requests | 3 |
| Successes | 3 |
| Fallbacks | 0 |
| Errors | 0 |
| Human review | 2 |
| Audit records | 3 |
| Audit failures | 0 |
| Models | 3 |

## Cockpit And Delivery Impact

| Scope | Value |
|---|---|
| Serving health | `healthy` |
| Serving metrics connected | true |
| Cockpit actions | 19 |
| Delivery backlog | 19 items |
| Ready to start | 15 |
| SLA tracked items | 16 |
| Due soon | 13 |

The previous `connect_serving_metrics_export` action is removed from the active delivery backlog because the metrics export is now connected. Remaining delivery pressure comes from solution blueprint, data contract coverage, promotion intake, promotion readiness and serving access governance work.

## Guardrails

- The export validates that summary counters match per-model totals.
- Negative counters are rejected.
- `export_status` is derived from metrics and cannot drift from the totals.
- Writing the checked-in snapshot builds the payload before opening the target path so an in-place refresh cannot truncate the source snapshot before it is read.
- The cockpit falls back to `metrics_not_connected` only when no metrics export is available.

## Next Step

Completed in Council 0055: model-serving is now packaged as an independently runnable AI Platform service boundary.

Next package retrieval as an independently runnable AI Platform service and harden model-serving deployment gates.
