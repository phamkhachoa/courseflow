# Council 0088: Runtime Product Readiness Freshness Probe

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| PO/BA | Make the AI spectrum coverage answer inspectable for release stakeholders |
| SA AI Platform | Prove product readiness is backed by a live runtime route, not only a static YAML snapshot |
| SA AI Engineer | Seed a tenant-safe runtime invocation and verify model-serving audit coverage |
| Governance Reviewer | Keep probe payloads free of raw identifiers and bind evidence to existing governance reports |
| Admin/Ops | Track the route freshness status before publishing it in the dashboard |

## Decision

Add `ai-platform-product-readiness-freshness-v1` as a product report under
`platform/product/reports`. The probe reuses the hosted model-serving adapter,
invokes `operations-demand-forecast-baseline-v1` with tenant-safe synthetic data,
then builds runtime product readiness from the adapter's live metrics snapshot.

## Runtime Evidence

| Surface | Result |
| --- | --- |
| Runtime route | `GET /v1/model-serving/product-readiness` is registered and returns HTTP 200 |
| Probe invocation | 1 tenant-safe runtime request is executed through the hosted adapter |
| Audit coverage | 1 audit record is written, with 0 audit failures |
| Serving health | Runtime readiness reports metrics connected, 0 errors and 0 audit gaps |
| AI spectrum | 8/8 required spectrum areas remain covered, with 6 extended enterprise modules |
| Static/runtime alignment | Checked-in product readiness summary aligns with the runtime readiness summary |

## Outcome

`platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml` now reports
`freshness_status=current`, `runtime_serving_request_count=1`,
`runtime_serving_audit_record_count=1`, `runtime_serving_error_count=0`,
`failed_check_count=0` and `covered_required_spectrum_count=8`.

## Next Step

Publish product readiness freshness into the Admin/Ops dashboard so release stakeholders can
see product readiness, route freshness and serving evidence in one operational view. This was
accepted in Council 0089; the next hardening step is tenant-safe incident export for stale or
failed freshness checks.
