# AI Platform Product Council 0038

Date: 2026-06-17

## Topic

Runtime observability in the AI Platform operating cockpit.

## Participants

- SA AI Platform: Cockpit projection and runtime health contract owner
- SA AI Engineer: Serving metrics and model-error triage owner
- PO/BA: Enterprise delivery visibility and acceptance owner
- Admin/Ops: Runtime monitoring and escalation owner

## Decision

Extend the AI Platform operating cockpit with a `servingHealth` projection built
from `ModelServingMetricsSnapshot`. The projection summarizes serving traffic,
model errors, fallbacks, human-review volume, audit record counts and audit
failure counts. When no runtime metrics snapshot is connected, the cockpit now
creates an explicit `connect_serving_metrics_export` action for SA AI Platform.

This turns model serving observability into a first-class delivery queue item
instead of leaving it as an implementation detail inside the gateway.

## Evidence

| Capability | Path |
|---|---|
| Serving health projection | `platform/src/courseflow_ai_platform/operating_cockpit.py` |
| Gateway metrics source | `platform/src/courseflow_ai_platform/model_serving.py` |
| Delivery backlog phase/criteria | `platform/src/courseflow_ai_platform/delivery_backlog.py` |
| Cockpit report | `platform/operations/reports/operating-cockpit-v1.yaml` |
| Delivery reports | `platform/delivery/reports/` |
| Tests | `platform/tests/test_operating_cockpit.py`, `platform/tests/test_delivery_backlog.py`, `platform/tests/test_delivery_sla.py`, `platform/tests/test_delivery_owner_views.py` |

## Runtime Health Statuses

| Status | Meaning |
|---|---|
| `metrics_not_connected` | Hosted serving metrics are not feeding the cockpit |
| `no_serving_traffic` | Metrics are connected but no traffic has arrived |
| `healthy` | Requests have matching audit records and no serving errors |
| `attention_required_audit_gap` | Serving traffic exists without full audit coverage |
| `degraded_by_model_serving_errors` | Model errors or fallbacks were observed |
| `blocked_by_model_audit_failure` | Audit write failures were observed |

## Delivery Impact

| Report | Change |
|---|---|
| Operating cockpit | 19 actions; serving health action added |
| Delivery backlog | Runtime observability phase added |
| Delivery SLA | Serving metrics export routed to SA AI Platform |
| Owner views | SA AI Platform queue now includes runtime observability work |

## Next Steps

1. Connect the hosted HTTP/gRPC adapter to publish `ModelServingMetricsSnapshot`.
2. Promote serving health to an Admin/Ops dashboard panel.
3. Add alert thresholds for audit failures, fallback rate and serving error rate.
