# Council 0087: Runtime Product Readiness Route

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| PO/BA | Let release stakeholders inspect product readiness through a service route |
| SA AI Platform | Reuse the model-serving service boundary instead of adding a separate app surface |
| SA AI Engineer | Bind readiness serving health to live model-serving metrics counters |
| Governance Reviewer | Keep readiness evidence tenant-safe and scoped to existing ops principals |
| Admin/Ops | Operate the route under the model-serving ops scope |

## Decision

Expose AI Platform product readiness through the model-serving runtime boundary at
`GET /v1/model-serving/product-readiness`. The route uses the same ops scope as
metrics, health and cockpit, and builds readiness from the adapter's live metrics snapshot.

## Runtime Evidence

| Surface | Result |
| --- | --- |
| Hosted adapter | `platform/src/courseflow_ai_platform/model_serving_adapter.py` serves product readiness from `snapshot_metrics()` |
| Auth policy | `platform/src/courseflow_ai_platform/model_serving_auth.py` maps the route to `internal:ai-platform:model-serving:ops` |
| Service package | `services/model-serving-service/service.yaml` declares the route and guardrail |
| CLI | `courseflow-model-serving product-readiness` calls the runtime route |
| Tests | Adapter and service contract tests verify runtime request/audit counts in readiness output |

## Outcome

After a model invocation, the runtime route returns `ai-platform-product-readiness-v1`
with `serving_status=healthy`, `serving_request_count=1`, `serving_audit_record_count=1`
and `readiness_status=stakeholder_ready_with_followups`. With no traffic, the route still
returns HTTP 200 and reports readiness body status as `blocked` instead of hiding the state.

## Next Step

Add a freshness probe for the runtime product-readiness route so Admin/Ops can distinguish
checked-in readiness snapshots from live route availability and recency.
