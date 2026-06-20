# Council 0065: LLM Provider Alert Routing Policy

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Add a tenant-safe LLM provider alert routing policy and generated report. The
AI Platform now validates that every observable provider has a budget/latency
route, Admin/Ops sink, escalation ref and rotation evidence stance before live
provider activation.

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Alert routing policy | `platform/governance/policies/llm-provider-alert-routing-policy.yaml` |
| Alert routing report | `platform/operations/reports/llm-provider-alert-routing-v1.yaml` |
| Alert routing builder | `platform/src/courseflow_ai_platform/llm_provider_alerts.py` |
| Cockpit projection | `platform/operations/reports/operating-cockpit-v1.yaml` |
| Admin/Ops dashboard | `platform/operations/reports/admin-ops-dashboard-v1.html` |
| Delivery backlog drill | `platform/delivery/reports/delivery-backlog-v1.yaml` |
| Tests | `platform/tests/test_llm_provider_alerts.py`, `platform/tests/test_operating_cockpit.py`, `platform/tests/test_delivery_backlog.py`, `platform/tests/test_admin_ops_dashboard.py`, `platform/tests/test_cli.py` |

## Guardrails

- Alert reports include provider IDs, route refs, sink refs and thresholds only.
- Credential refs, provider API keys, prompt payloads and raw service/tenant IDs
  are omitted from the alert routing report.
- Contract-stub providers must not declare live rotation refs.
- Live network providers must declare rotation automation and rotation evidence
  refs before `live_alert_ready`.
- Cockpit action changes from alert configuration to Admin/Ops alert delivery
  drill once every observable provider has a valid route.

## Product Impact

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | RAG Tutor and auto-grading inherit the same provider alert route gate |
| Support Platform | Agent assist gets Admin/Ops alert route drill evidence before live providers |
| Billing/Finance | Finance assistants inherit provider budget and latency escalation routing |
| AI Platform | Provider alert routing becomes a validated platform control-plane artifact |

## Next Step

Council 0066 added the secret rotation control plane. Next, enable a live
network provider only after approved secret-manager refs, rotation evidence and
alert-route drill evidence exist outside source control.
