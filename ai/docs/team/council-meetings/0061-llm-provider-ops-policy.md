# Council 0061: LLM Provider Ops Policy

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Add a provider-operations policy for the LLM adapter service before live provider
credentials are connected. The adapter now treats rate limits, timeouts,
circuit-breaker thresholds and failover provider chains as governed policy, not
application constants.

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Provider ops policy | `platform/governance/policies/llm-provider-ops-policy.yaml` |
| Runtime enforcement | `platform/src/courseflow_ai_platform/llm_provider_adapter.py` |
| Service contract | `services/llm-adapter-service/service.yaml` |
| Platform tests | `platform/tests/test_llm_provider_adapter.py` |
| Service tests | `services/llm-adapter-service/tests/test_service_contract.py` |

## Guardrails

- Prompt Gateway remains mandatory before provider calls.
- Provider calls are rate-limited by principal, tenant, product, use case and provider.
- Live network providers must use non-local credential references.
- Primary provider failures can fail over only to configured, granted providers.
- Rate-limit and failover counters are exposed through adapter metrics.

## Product Impact

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | RAG Tutor and auto-grading inherit provider quotas and failover policy |
| Support Platform | Agent assist can fail over without bypassing Prompt Gateway |
| Billing/Finance | Reconciliation/document assistants inherit stricter provider ops controls |
| AI Platform | Admin/Ops has policy evidence before live provider credentials are wired |

## Next Step

Completed in Council 0062 and 0063: the LLM adapter now has a generated
provider credential readiness report plus runtime probe/cost-latency evidence.

Council 0066 added the secret rotation control plane. Next, enable live provider
network access only after approved secret-manager refs and rotation evidence are
available outside source control.
