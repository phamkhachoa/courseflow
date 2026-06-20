# CourseFlow Model Serving Service

Canonical location: `ai/services/model-serving-service`.

This is the independent runtime shell for AI Platform model serving. It packages the existing
manifest-backed serving facade, hosted adapter, route-scope authorization, audit hook and metrics
export as a service boundary that can be run without importing LMS code.

## Responsibilities

- Expose the shared model-serving routes:
  - `GET /v1/models`
  - `POST /v1/model-invocations`
  - `GET /v1/model-serving/metrics`
  - `GET /v1/model-serving/health`
  - `GET /v1/model-serving/cockpit`
  - `GET /v1/model-serving/product-readiness`
- Enforce route scopes and principal grants from AI Platform governance policy.
- Dispatch model invocations through `courseflow_ai_platform.model_serving`.
- Persist sanitized model audit records when an audit log path is configured.
- Export model-serving metrics snapshots for the operating cockpit.
- Serve AI Platform product readiness from live model-serving metrics for release stakeholders.

## Local Development

```bash
cd ai/services/model-serving-service
make test
make health
```

Invoke an enterprise operations model through the service boundary:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_model_serving_service.cli \
  --ai-root ../.. \
  --principal-id service:enterprise-operations-serving \
  invoke \
  --body-json '{"requestId":"req-local-1","tenantId":"tenant-ops","modelId":"operations-demand-forecast-baseline-v1","payload":{"tenant_id":"tenant-ops","forecast_id":"fc-local-1","queue_id":"support-identity","historical_demand":[78,82,84,96,114,132],"planned_capacity":110,"backlog_open_items":28,"avg_handle_minutes":52,"seasonal_index":1.08,"special_event":true,"incident_open":true,"forecast_horizon_days":7,"service_level_target":0.92}}'
```

Run the lightweight HTTP wrapper:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_model_serving_service.cli \
  --ai-root ../.. \
  serve \
  --host 127.0.0.1 \
  --port 8091
```

The HTTP wrapper expects `X-CourseFlow-Principal-Id`; it resolves the route scope from
`model-serving-access-policy.yaml` before handing the request to the hosted adapter.

Inspect runtime product readiness through the ops principal:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_model_serving_service.cli \
  --ai-root ../.. \
  --principal-id service:ai-platform-ops \
  product-readiness
```
