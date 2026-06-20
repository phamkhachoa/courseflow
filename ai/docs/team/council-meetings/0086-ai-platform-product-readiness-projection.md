# Council 0086: AI Platform Product Readiness Projection

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| PO/BA | Make AI Platform release readiness visible as product evidence |
| SA AI Platform | Define readiness gates that prove the platform product can serve many domains |
| SA AI Engineer | Bind evaluation, serving metrics and response-runbook evidence to deterministic checks |
| Governance Reviewer | Keep incident and response evidence tenant-safe |
| Admin/Ops | Confirm dashboard freshness and accepted incident response are release-facing gates |

## Decision

Add `ai-platform-product-readiness-v1` as the product-facing readiness projection for the
Enterprise AI Platform. The report turns the accepted Governance Evaluation response runbook
from Council 0085 into a required readiness gate, alongside coverage, evaluation, release,
serving, dashboard freshness and tenant-safe incident evidence.

## Required Gates

| Gate | Owner | Current status |
| --- | --- | --- |
| AI Platform product registered | PO/BA | passed |
| Required AI spectrum covered | SA AI Platform | passed |
| Required evaluation gates pass | SA AI Engineer | passed |
| Release health is ready | SA AI Platform + Governance Reviewer | passed |
| Serving metrics are healthy | Admin/Ops | passed |
| Admin/Ops dashboard is current | Admin/Ops | passed |
| Incident exports are tenant-safe and quiet | Governance Reviewer | passed |
| Governance Evaluation response runbook is accepted | Admin/Ops | passed |

## Outcome

The current product readiness status is `stakeholder_ready_with_followups`:
8/8 required gates passed, 0 blocking actions, 0 open incidents, 1 serving-access watch item
and tenant-safe evidence. The remaining follow-up is to serve product readiness from runtime
service metrics rather than relying only on checked-in file-backed reports.

## Surfaces

| Surface | Result |
| --- | --- |
| Module | `platform/src/courseflow_ai_platform/product_readiness.py` |
| Report | `platform/product/reports/ai-platform-product-readiness-v1.yaml` |
| CLI | `--write-ai-platform-product-readiness-report` |
| Product registry | `products/registry.yaml` includes the readiness report as an AI Platform artifact |
| Tests | `platform/tests/test_product_readiness.py` and CLI coverage |

## Next Step

Serve the product readiness dashboard from model-serving/runtime metrics so release stakeholders
can compare static release evidence with live service health before production rollout.
